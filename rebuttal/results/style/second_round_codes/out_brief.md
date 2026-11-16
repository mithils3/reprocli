# Coder brief: reviewer comments (stated position)

You code twenty review-discussion threads from one shard file. Each block starts with a line "## tNNN" (the code), then "REVIEWER COMMENT 1:" (the reviewer's first comment after the authors' first reply) and "REVIEWER LATER COMMENTS:" (everything the same reviewer wrote later in the thread). Code only what the reviewer's text states.

For each thread write one JSON object on one line with exactly these keys:
- "code": the tNNN code.
- "c1_states_raise": true only if comment 1 says the reviewer raises, increases or has updated the score or rating upward.
- "c1_states_keep": true only if comment 1 says the reviewer keeps, maintains or will not change the score or rating.
- "later_states_raise": true only if the later comments say the reviewer raises, increases, or has updated the score or rating upward, or now recommends acceptance after not doing so.
- "later_states_keep": true only if the later comments say the reviewer keeps, maintains or will not raise the score or rating.
- "later_states_lower": true only if the later comments say the reviewer lowers the score or rating.
- "later_new_score": the new numeric score if the later comments state one, else null.
- "later_stance": one of "satisfied" (concerns resolved), "partly" (some remain), "unconvinced" (main concern remains), "unclear".

Booleans are strict: true needs an explicit statement; thanks or praise alone is not a raise. Use JSON true/false/null and the exact strings above.

Output: write the twenty lines, in the shard's order, to the output file named in your task, with the Write tool. Then run the check command from your task and fix the file until it prints OK. Read only your shard file and this brief. No network. Your final message is the check command's last line.
