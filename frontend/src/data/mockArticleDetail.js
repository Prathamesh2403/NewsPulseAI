// Mock article detail data
// Structure mirrors GET /api/v1/articles/:id response.
// Swap the hook internals to fetch from the real API later.

export const MOCK_ARTICLE_DETAIL = {
  id: 'art-001',
  title: 'OpenAI Unveils GPT-5 with Unprecedented Reasoning Capabilities',
  source: 'TechCrunch',
  date: '2025-06-15T18:30:00Z',
  image: 'https://picsum.photos/800/400?random=42',
  category: 'LLMs',
  breadcrumbSource: 'TechCrunch',
  sentiment: 'positive',
  content: [
    "OpenAI has officially announced GPT-5, the latest iteration of its flagship large language model, marking what many industry observers are calling a generational leap in artificial intelligence capabilities. The new model demonstrates remarkable improvements in multi-step reasoning, mathematical problem-solving, and code generation, achieving state-of-the-art scores across a battery of graduate-level benchmarks that have long served as the gold standard for evaluating AI systems.",
    "In a live demonstration at the company's San Francisco headquarters, CEO Sam Altman showcased GPT-5's ability to solve complex physics problems, write production-ready software from high-level specifications, and engage in nuanced debates about philosophical topics -- all with a level of coherence and accuracy that visibly impressed the assembled journalists and researchers. The model's architecture incorporates a novel \"chain-of-thought\" reasoning engine that allows it to break down complex problems into intermediate steps, dramatically reducing the hallucination rates that have plagued earlier versions.",
    "The release has sent shockwaves through the AI industry, with competitors scrambling to respond. Anthropic, Google DeepMind, and Meta AI have all acknowledged the significance of the achievement, though each has pointed to their own ongoing research efforts as evidence that the race is far from over. Wall Street reacted positively, with OpenAI's valuation now estimated to exceed $300 billion following the announcement, making it one of the most valuable private companies in history.",
    "However, not everyone is celebrating. Safety researchers have raised concerns about the pace of development, arguing that GPT-5's capabilities bring the field closer to artificial general intelligence than many had anticipated. The model's ability to autonomously plan and execute multi-step tasks across different domains has reignited debates about alignment, governance, and the need for international regulatory frameworks. OpenAI has committed to a phased rollout, with enterprise customers gaining access first and consumer availability expected within the coming weeks."
  ],
  comments: [
    {
      id: 'cmt-1',
      username: '/u/AIEnthusiast',
      avatar: null,
      text: "This is genuinely impressive. I ran the benchmark comparisons myself and the reasoning improvements are not incremental -- they represent a fundamental shift. The chain-of-thought engine is doing something qualitatively different from what we have seen before.",
      upvotes: 182,
    },
    {
      id: 'cmt-2',
      username: '/u/ml_researcher_22',
      avatar: null,
      text: "I am cautiously optimistic. The demo was compelling but I want to see independent evaluations before drawing conclusions. We have been burned before by cherry-picked examples. That said, the architecture paper is solid and the theoretical foundations check out.",
      upvotes: 97,
    },
    {
      id: 'cmt-3',
      username: '/u/TechSkeptic',
      avatar: null,
      text: "Am I the only one concerned about the safety implications? We are moving incredibly fast with very little regulatory oversight. The fact that it can autonomously plan multi-step tasks is exactly the kind of capability that alignment researchers have been warning about for years.",
      upvotes: 64,
    },
  ],
}
