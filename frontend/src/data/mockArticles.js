// Mock article data
// Structure mirrors GET /api/v1/articles response so swapping to real API
// only requires changing the data-fetching hook, not any UI components.

export const MOCK_ARTICLES = [
  {
    id: 'art-001',
    title: 'OpenAI Unveils GPT-5 with Unprecedented Reasoning Capabilities',
    source: 'TechCrunch',
    timestamp: '2025-06-15T18:30:00Z',
    snippet:
      'The new model achieves state-of-the-art scores on graduate-level math and coding benchmarks, signaling a major leap in language model reasoning.',
    thumbnail: 'https://picsum.photos/80/80?random=1',
    category: 'LLMs',
    sentiment: 'positive',
  },
  {
    id: 'art-002',
    title: 'NVIDIA Announces Blackwell Ultra GPUs at Record $40,000 Per Unit',
    source: 'The Verge',
    timestamp: '2025-06-15T17:10:00Z',
    snippet:
      "NVIDIA's latest data center chips deliver 2x the performance of Hopper, but their stratospheric price tag raises accessibility concerns for smaller labs.",
    thumbnail: 'https://picsum.photos/80/80?random=2',
    category: 'Hardware',
    sentiment: 'neutral',
  },
  {
    id: 'art-003',
    title: 'EU AI Act Enforcement Begins: What It Means for US Tech Giants',
    source: 'Reuters',
    timestamp: '2025-06-15T15:45:00Z',
    snippet:
      'Brussels has started issuing compliance notices to major AI providers, with fines up to 3% of global annual revenue for high-risk system violations.',
    thumbnail: 'https://picsum.photos/80/80?random=3',
    category: 'Policy',
    sentiment: 'negative',
  },
  {
    id: 'art-004',
    title: 'Anthropic Raises $2.5B Series E Led by Google at $50B Valuation',
    source: 'Bloomberg',
    timestamp: '2025-06-15T14:00:00Z',
    snippet:
      "The funding round cements Anthropic's position as the second most valuable AI startup, with Google deepening its strategic partnership.",
    thumbnail: 'https://picsum.photos/80/80?random=4',
    category: 'Startups',
    sentiment: 'positive',
  },
  {
    id: 'art-005',
    title: "Boston Dynamics' Atlas Robot Learns to Cook Breakfast Autonomously",
    source: 'MIT Technology Review',
    timestamp: '2025-06-15T12:20:00Z',
    snippet:
      'In a viral demo, Atlas cracked eggs, operated a stovetop, and plated a meal -- tasks that require dexterous manipulation once considered decades away.',
    thumbnail: 'https://picsum.photos/80/80?random=5',
    category: 'Robotics',
    sentiment: 'positive',
  },
  {
    id: 'art-006',
    title: "Meta's Llama 4 Open-Weights Model Tops Leaderboards, Stirs Debate",
    source: 'Wired',
    timestamp: '2025-06-15T11:00:00Z',
    snippet:
      "Llama 4's release reignites the open vs. closed AI debate as its performance rivals GPT-4o, but researchers flag safety evaluation gaps.",
    thumbnail: 'https://picsum.photos/80/80?random=6',
    category: 'LLMs',
    sentiment: 'neutral',
  },
  {
    id: 'art-007',
    title: "Intel's Gaudi 4 AI Accelerator Struggles to Compete with NVIDIA in Benchmarks",
    source: 'Ars Technica',
    timestamp: '2025-06-15T09:30:00Z',
    snippet:
      "Independent tests show Intel's latest AI chip falling 30-40% short of H200 throughput on transformer workloads, clouding its data center ambitions.",
    thumbnail: 'https://picsum.photos/80/80?random=7',
    category: 'Hardware',
    sentiment: 'negative',
  },
  {
    id: 'art-008',
    title: 'AI Drug Discovery Startup Isomorphic Labs Completes Phase 1 Trial',
    source: 'Nature News',
    timestamp: '2025-06-15T08:15:00Z',
    snippet:
      "DeepMind's spinout reported positive safety results for an AI-designed compound targeting a previously undruggable protein linked to pancreatic cancer.",
    thumbnail: 'https://picsum.photos/80/80?random=8',
    category: 'Startups',
    sentiment: 'positive',
  },
]

// Sidebar / chart data
export const SENTIMENT_TREND = [
  { day: 'Mon', positive: 52, neutral: 30, negative: 18 },
  { day: 'Tue', positive: 48, neutral: 32, negative: 20 },
  { day: 'Wed', positive: 60, neutral: 25, negative: 15 },
  { day: 'Thu', positive: 55, neutral: 28, negative: 17 },
  { day: 'Fri', positive: 63, neutral: 22, negative: 15 },
  { day: 'Sat', positive: 58, neutral: 27, negative: 15 },
  { day: 'Sun', positive: 65, neutral: 24, negative: 11 },
]

export const CATEGORY_SHARE = [
  { name: 'LLMs', value: 32, color: '#7F77DD' },
  { name: 'Hardware', value: 22, color: '#3ECFB4' },
  { name: 'Startups', value: 20, color: '#F0A96D' },
  { name: 'Policy', value: 14, color: '#F06D6D' },
  { name: 'Robotics', value: 12, color: '#71717A' },
]

export const STATS = {
  articlesToday: 307,
  articlesTodayChange: '+4.5%',
  topCategory: 'LLMs',
  topCategoryPct: '32%',
}
