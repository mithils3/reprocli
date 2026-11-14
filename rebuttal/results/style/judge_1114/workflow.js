export const meta = {
  name: 'reply-blind-rank',
  description: 'Blind-rank the Reviewer 3 reply among 240 real ICLR author replies, then head-to-head and reviewer-view audits',
  phases: [
    { title: 'Blind rank', detail: '30 judges, each 8 real replies plus ours, source and outcome hidden', model: 'haiku' },
    { title: 'Pointer check', detail: 'every section pointer and number against the frozen PDF text', model: 'haiku' },
    { title: 'Head to head', detail: 'ours against the 15 top-ranked real replies, blind', model: 'fable' },
    { title: 'Audit', detail: 'read as Reviewer YGTR and as the area chair', model: 'fable' },
  ],
}
const { dir, ours, h2h } = args
const REPO = '/home/mithil/PyCharmProjects/reprocli'
const oursSet = new Set(ours.concat(h2h))
const pad = n => String(n).padStart(2, '0')
const norm = id => String(id).replace(/\.txt$/, '').replace(/^.*\//, '').trim()

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    threads: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          n_points: { type: 'integer' },
          n_direct: { type: 'integer' },
          coverage: { type: 'integer' },
          evidence: { type: 'integer' },
          clarity: { type: 'integer' },
          tone: { type: 'integer' },
          overall: { type: 'integer' },
          p_convinced: { type: 'integer' },
          weakness: { type: 'string' },
        },
        required: ['id', 'n_points', 'n_direct', 'coverage', 'evidence', 'clarity', 'tone', 'overall', 'p_convinced', 'weakness'],
      },
    },
    ranking: { type: 'array', items: { type: 'string' } },
  },
  required: ['threads', 'ranking'],
}

const judgePrompt = s => `You are an experienced ICLR reviewer judging author replies.

Read the list file ${dir}/shards/shard_${pad(s)}.txt with the Read tool. It names 9 text files. Read all 9 in full with the Read tool, one call per file, before you score anything. Each file holds one review of a machine learning paper and the authors' first reply to that review; some also hold the authors' general response to all reviewers as context. The 9 files come from 9 different papers.

Judge only how well each reply answers its own review. Do not judge the paper's topic, the field, the year, or how harsh the review is. Do not search the web, do not open any other file, and do not try to identify the papers.

For each file return:
- id: the file name without ".txt".
- n_points: the number of distinct weaknesses and questions in the review.
- n_direct: how many of those the reply answers directly, with a result, a number, a concrete change to the paper, or a reasoned argument.
- coverage, evidence, clarity, tone, overall: integers from 1 (poor) to 10 (excellent). coverage = every point answered and none dodged. evidence = new experiments, numbers or analyses that bear on the reviewer's doubts. clarity = the answer comes first, it is easy to follow, and the length fits. tone = respectful and level; take points off for defensiveness, condescension, flattery or coldness. overall = how good the reply is as an answer to this review.
- p_convinced: an integer from 0 to 100, your probability that a reviewer who scored the paper just below the accept line would move to the accept line after reading this reply.
- weakness: the reply's single biggest weakness, in at most 25 words.

Then return ranking: all 9 ids ordered from the best reply to the worst, with no ties. Use the full range of the scales; the 9 replies differ in quality. Return the result through the StructuredOutput tool and nothing else.`

const H2H_SCHEMA = {
  type: 'object',
  properties: {
    ranking: { type: 'array', items: { type: 'string' } },
    replies: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          strongest_move: { type: 'string' },
          biggest_weakness: { type: 'string' },
          would_move_reviewer: { type: 'boolean' },
          best_edits: { type: 'array', items: { type: 'string' } },
        },
        required: ['id', 'strongest_move', 'biggest_weakness', 'would_move_reviewer', 'best_edits'],
      },
    },
    transferable_moves: { type: 'array', items: { type: 'string' } },
  },
  required: ['ranking', 'replies', 'transferable_moves'],
}

const h2hPrompt = paths => `You are a senior ICLR area chair comparing six author replies. Read these six files in full with the Read tool:
${paths.join('\n')}

Each file holds one review of a machine learning paper and the authors' first reply to it (some also hold the authors' general response as context). They come from six different papers. Judge only how well each reply answers its own review, as the reviewer who wrote that review would experience it. Do not search the web, do not open other files, and do not try to identify the papers.

Return through StructuredOutput:
- ranking: the six ids (file name without ".txt") from best reply to worst, no ties.
- replies: for each id, strongest_move (the most effective thing the reply does, with a short quote), biggest_weakness (the thing most likely to leave the reviewer unconvinced or irritated, with a short quote), would_move_reviewer (true if you expect a reviewer just below the accept line to move to it), and best_edits (the three specific wording or structure edits that would most improve that reply, each at most 40 words, using only content already in the reply).
- transferable_moves: up to eight concrete things the higher-ranked replies do that the lower-ranked ones lack, each naming the ids it is drawn from.`

const RULES = `Rules for anything you propose. The numbers are frozen and no new result can be added, so propose wording, order, structure and cuts only, or flag an error. Each comment must stay under 5,000 characters (they are at 4,834 and 4,876), so every addition names a cut of equal length. Do not propose an admission of a weakness the reviewer did not ask about, a sentence that says or implies the reviewer misread, a sentence that says the paper already states something, or any mention of work that is running or queued. Proposed text uses plain connected sentences, no em dashes, and no "X, not Y" contrast frames. Do not edit any file under ${REPO}; write only the one report file named below.`

const reviewerPrompt = `Why fable: this is judgment on text a paper reviewer will act on, with no mechanical check.

Read as Reviewer YGTR of ICLR 2027 submission 22528 (RECLAIM), who gave rating 2 on a 4-point scale (3 is the accept line), soundness 2 and informativeness 1. Read only the section "## Reviewer YGTR" of ${REPO}/rebuttal/reviews-2026-11-06.md (ignore the PAT section and the other reviewers), then the authors' reply to you in ${REPO}/rebuttal/post/YGTR_1.md and ${REPO}/rebuttal/post/YGTR_2.md (two OpenReview comments, in that order), and the general reply ${REPO}/rebuttal/post/general.md. You may consult the revised paper's text at ${dir}/../freeze_pdf.txt (search it with rg; it is long) to check that a pointed-to section says what the reply says.

Write a report to ${dir}/out/audit_reviewer.md with these parts: (1) for each of your points (each weakness and Q1 to Q3), a verdict resolved, partly resolved or not resolved, with the sentence of the reply that decides it; (2) the follow-up questions you would most likely post, most likely first; (3) whether you would move from 2 to 3, with the one thing that would change your mind either way; (4) every sentence that reads as cold, defensive, condescending, evasive, overclaiming or hard to follow, quoted, with a replacement; (5) the five edits that would most raise the chance you move to 3, in order, each with exact old text and exact new text and the character change.

${RULES}

Return a summary of at most 300 words: the verdict per point, whether you would raise, and the top five edits.`

const acPrompt = `Why fable: this is judgment on text reviewers and the area chair will act on, with no mechanical check.

Read as the area chair of ICLR 2027 submission 22528 (RECLAIM), who reads all reviews and all author replies together. Read ${REPO}/rebuttal/reviews-2026-11-06.md (the three reviewers T29u, rqBN and YGTR; ignore the PAT section), the two replies already posted and no longer editable (${REPO}/rebuttal/post/T29u_1.md and ${REPO}/rebuttal/post/rqBN_1.md), and the three texts about to be posted (${REPO}/rebuttal/post/YGTR_1.md, ${REPO}/rebuttal/post/YGTR_2.md, ${REPO}/rebuttal/post/general.md).

Write a report to ${dir}/out/audit_ac.md with these parts: (1) every number or claim in the YGTR comments or the general reply that conflicts with, or sits awkwardly beside, a number or claim in the two posted replies, quoted from both sides; (2) whether the YGTR reply stands by itself for a reader who does not open the paper; (3) what in the YGTR reply an area chair would count for the paper and what against; (4) whether the general reply does its job (thanks, what reviewers valued, the list of changes with locations, results that answer several reviewers), and what in it repeats the reviewer replies without need; (5) the five edits to the unposted texts that matter most, each with exact old text, exact new text and the character change.

${RULES}

Return a summary of at most 300 words: the conflicts found, and the top five edits.`

const POINTER_SCHEMA = {
  type: 'object',
  properties: {
    checked: { type: 'integer' },
    problems: {
      type: 'array',
      items: {
        type: 'object',
        properties: { quote: { type: 'string' }, problem: { type: 'string' }, pdf_evidence: { type: 'string' } },
        required: ['quote', 'problem', 'pdf_evidence'],
      },
    },
  },
  required: ['checked', 'problems'],
}
const pointerPrompt = i => `Mechanical check of one author reply against the text of the paper's PDF. Read ${REPO}/rebuttal/post/YGTR_${i}.md. The PDF's text layer is ${dir}/../freeze_pdf.txt (about 440,000 characters; search it with rg -n and read around hits with the Read tool's offset and limit, never the whole file at once).

For every place where the reply points to the paper, such as "(Section 5.2, Appendix B.3)", list the numbers and claims of the sentences that pointer covers, and check that the named section or appendix of the PDF text holds each one. Section headings in the text file may be letter-spaced, so search for distinctive numbers and phrases instead (for example "23 of 27", "0.11", "5.6").

Report as a problem only: a pointed-to section that does not exist, or a number in the reply that the pointed-to section states differently. A number that the reply gives and the paper simply does not repeat is not a problem; do not report it. Count in "checked" how many number-and-pointer pairs you checked. For each problem give the reply's sentence (quote), what differs (problem) and the PDF line you found (pdf_evidence). Do not edit any file. Return through StructuredOutput.`

// Audits and pointer checks start now and run beside the ranking (2 fable + 2 haiku).
const sidePromise = parallel([
  () => agent(reviewerPrompt, { label: 'audit:as-reviewer-YGTR', phase: 'Audit', model: 'fable', effort: 'high', agentType: 'general-purpose' }),
  () => agent(acPrompt, { label: 'audit:as-area-chair', phase: 'Audit', model: 'fable', effort: 'high', agentType: 'general-purpose' }),
  () => agent(pointerPrompt(1), { label: 'pointers:comment-1', phase: 'Pointer check', model: 'haiku', effort: 'medium', agentType: 'lean', schema: POINTER_SCHEMA }),
  () => agent(pointerPrompt(2), { label: 'pointers:comment-2', phase: 'Pointer check', model: 'haiku', effort: 'medium', agentType: 'lean', schema: POINTER_SCHEMA }),
])

phase('Blind rank')
// Barrier: the head-to-head stage needs the top-ranked replies across all 30 shards.
const judged = (await parallel(Array.from({ length: 30 }, (_, s) => () =>
  agent(judgePrompt(s), { label: `judge:shard-${pad(s)}`, phase: 'Blind rank', model: 'haiku', effort: 'medium', agentType: 'lean', schema: JUDGE_SCHEMA })
    .then(r => r && { shard: s, threads: r.threads.map(t => ({ ...t, id: norm(t.id) })), ranking: r.ranking.map(norm) })
))).filter(Boolean)
log(`${judged.length} of 30 shards judged`)

const rows = judged.flatMap(j => j.threads.map(t => ({ ...t, shard: j.shard, rank: j.ranking.indexOf(t.id) + 1 })))
const tops = rows.filter(r => !oursSet.has(r.id))
  .sort((a, b) => (b.overall - a.overall) || (a.rank - b.rank) || (b.p_convinced - a.p_convinced))
  .slice(0, 15)
log(`top 15 real replies picked for the head-to-head (overall ${tops.map(t => t.overall).join(',')})`)

phase('Head to head')
// Why fable: comparative judgment of reviewer-facing replies with no mechanical check; three at once, five with the two audits.
const h2hRes = await parallel([0, 1, 2].map(j => () => {
  const five = [0, 3, 6, 9, 12].map(k => tops[j + k]).filter(Boolean).map(t => `${dir}/packets/${t.id}.txt`)
  const pos = (2 * j + 1) % (five.length + 1)
  const paths = five.slice(0, pos).concat([`${dir}/packets/${h2h[j]}.txt`], five.slice(pos))
  return agent(h2hPrompt(paths), { label: `h2h:set-${j}`, phase: 'Head to head', model: 'fable', effort: 'high', agentType: 'general-purpose', schema: H2H_SCHEMA })
    .then(r => r && { set: j, ours_id: h2h[j], ...r })
}))

const side = await sidePromise
return { judged, tops: tops.map(t => ({ id: t.id, overall: t.overall, shard: t.shard })), h2h: h2hRes.filter(Boolean), audit_reviewer: side[0], audit_ac: side[1], pointers: [side[2], side[3]] }
