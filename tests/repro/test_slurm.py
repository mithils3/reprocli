from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reprocli_repro.cluster import Cluster, resolve_cluster
from reprocli_repro.slurm import (
    StepResult,
    acquire_session,
    build_acquire,
    build_srun,
    release_session,
    run_in_session,
    session_lost,
)


class BuildAcquireTests(unittest.TestCase):
    def test_builds_a_held_salloc_for_deltaai(self):
        argv = build_acquire(resolve_cluster("deltaai"), gpus=4, minutes=90)
        self.assertEqual(argv[0], "salloc")
        # --no-shell holds the allocation and returns once granted (no step runs yet).
        self.assertIn("--no-shell", argv)
        self.assertIn("-A", argv)
        self.assertIn("betw-dtai-gh", argv)
        self.assertIn("-p", argv)
        self.assertIn("ghx4", argv)
        self.assertIn("--gpus=4", argv)
        self.assertIn("--time=90", argv)
        # Acquire holds the node only; the command is spliced in later by build_srun.
        self.assertNotIn("srun", argv)

    def test_partition_override_replaces_the_profile_default(self):
        # The model picks a pool (from list_partitions) without touching the account.
        argv = build_acquire(
            resolve_cluster("deltaai"), gpus=1, minutes=10, partition="ghx4-interactive"
        )
        self.assertIn("ghx4-interactive", argv)
        self.assertNotIn("ghx4", [a for a in argv if a == "ghx4"])  # default not used
        self.assertIn("betw-dtai-gh", argv)  # account still the profile's

    def test_partition_override_satisfies_a_profile_without_a_default(self):
        # A bare cluster (no pinned partition) is allocatable once the model names one.
        bare = Cluster(name="bare", hw="h100", gpus_per_node=1, account="acct")
        argv = build_acquire(bare, gpus=1, minutes=5, partition="some-pool")
        self.assertIn("some-pool", argv)

    def test_rejects_profile_without_account(self):
        bare = Cluster(name="bare", hw="h100", gpus_per_node=1)
        with self.assertRaises(SystemExit):
            build_acquire(bare, gpus=1, minutes=1)

    def test_rejects_gpus_over_node_capacity(self):
        with self.assertRaises(SystemExit):
            build_acquire(resolve_cluster("deltaai"), gpus=8, minutes=1)


class BuildSrunTests(unittest.TestCase):
    def test_runs_into_held_jobid_bare_without_sandbox(self):
        argv = build_srun(resolve_cluster("deltaai"), "/ws", "python train.py", jobid="2542640")
        self.assertEqual(argv[0], "srun")
        self.assertIn("--jobid=2542640", argv)
        self.assertIn("--ntasks=1", argv)
        inner = argv[-1]
        # No sandbox passed -> bare body; CUDA comes from the image at runtime, not a
        # host `module load`, so the payload carries neither.
        self.assertNotIn("apptainer", inner)
        self.assertNotIn("module load", inner)
        self.assertEqual(inner, "cd /ws && python train.py")

    def test_sandbox_splices_apptainer_after_srun(self):
        from reprocli_repro.sandbox import CONTAINER_WORKSPACE, Bind, Sandbox

        sb = Sandbox(image="/img.sif", binds=(Bind("/host/ws", CONTAINER_WORKSPACE),))
        argv = build_srun(resolve_cluster("deltaai"), "/host/ws", "python train.py", jobid="42", sandbox=sb)
        # srun (the trusted launcher) stays outside; the apptainer wrap is spliced after,
        # and the payload cd's to the short container workdir.
        self.assertEqual(argv[0], "srun")
        self.assertIn("--jobid=42", argv)
        self.assertIn("apptainer", argv)
        self.assertIn("--nv", argv)  # GPU step
        self.assertEqual(argv[-3:], ["bash", "-lc", "cd /repro/workspace && python train.py"])


class AcquireSessionTests(unittest.TestCase):
    def test_parses_granted_jobid(self):
        granted = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="",
            stderr="salloc: Pending job allocation 2542640\nsalloc: Granted job allocation 2542640\n",
        )
        with mock.patch("reprocli_repro.slurm.subprocess.run", return_value=granted) as run:
            handle = acquire_session(resolve_cluster("deltaai"), gpus=1, minutes=5)
        self.assertTrue(handle.ok, handle.stderr)
        self.assertEqual(handle.jobid, "2542640")
        self.assertEqual(run.call_args.args[0][0], "salloc")

    def test_failed_acquire_has_no_jobid(self):
        failed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="salloc: error: Unable to allocate resources\n"
        )
        with mock.patch("reprocli_repro.slurm.subprocess.run", return_value=failed):
            handle = acquire_session(resolve_cluster("deltaai"), gpus=1, minutes=5)
        self.assertFalse(handle.ok)
        self.assertIsNone(handle.jobid)


class RunInSessionTests(unittest.TestCase):
    def test_runs_srun_into_session_and_populates_result(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="hello-step\n", stderr="")
        with mock.patch("reprocli_repro.slurm.subprocess.run", return_value=fake) as run:
            result = run_in_session(resolve_cluster("deltaai"), "/ws", "echo hello-step", jobid="9")
        self.assertTrue(result.ok, result.stderr)
        self.assertIn("hello-step", result.stdout)
        self.assertGreaterEqual(result.elapsed_s, 0.0)
        self.assertEqual(run.call_args.args[0][0], "srun")


class ReleaseAndLostTests(unittest.TestCase):
    def test_release_session_scancels(self):
        with mock.patch("reprocli_repro.slurm.subprocess.run") as run:
            release_session("2542640")
        self.assertEqual(run.call_args.args[0], ["scancel", "2542640"])

    def test_session_lost_detects_expired_allocation(self):
        lost = StepResult(
            ok=False, returncode=1, stdout="",
            stderr="srun: error: Unable to confirm allocation for job 555: Invalid job id specified",
            elapsed_s=0.1, command=["srun"],
        )
        ok = StepResult(ok=True, returncode=0, stdout="x", stderr="", elapsed_s=0.1, command=["srun"])
        self.assertTrue(session_lost(lost))
        self.assertFalse(session_lost(ok))

    def test_session_lost_detects_time_wall_expiry(self):
        # A held allocation that hit its --time wall drains COMPLETING -> EXPIRED; each
        # stage produces a distinct srun message and every one must drop the session so
        # the next run_gpu re-acquires instead of hammering the dead jobid.
        for stderr in (
            "srun: error: Unable to create step for job 2564702: Job/step already completing or completed",
            "srun: error: Slurm job 2564702 has expired",
            "srun: Check SLURM_JOB_ID environment variable. Expired or invalid job 2564702",
        ):
            step = StepResult(ok=False, returncode=1, stdout="", stderr=stderr, elapsed_s=0.1, command=["srun"])
            self.assertTrue(session_lost(step), stderr)


if __name__ == "__main__":
    unittest.main()
