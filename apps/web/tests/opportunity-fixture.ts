import type { components } from '../src/lib/api/schema';
export const id = '11111111-1111-4111-8111-111111111111';
export const time = '2026-10-12T00:00:00Z';
export const citation = {
  source_url: 'https://example.invalid/synthetic-test-policy',
  passage: 'Synthetic test clause: applicants must be at least eighteen.',
  page: '1',
};
export const rule = {
  op: 'condition' as const,
  condition: { op: 'gte' as const, fact: 'age' as const, value: 18 },
};
export const opportunity: components['schemas']['OpportunityView'] = {
  id,
  version: 1,
  publication_state: 'published',
  is_synthetic: false,
  title: 'Synthetic browser test policy',
  summary: 'Fictional policy for testing the browser contract only.',
  category: 'education',
  issuer: 'Synthetic test authority',
  status: 'verified',
  country: 'India',
  state: null,
  district: null,
  applicability: [],
  benefits: null,
  restrictions: [],
  required_documents: [],
  opens_on: null,
  closes_on: null,
  apply_url: null,
  source_url: citation.source_url,
  first_seen_at: time,
  last_verified_at: time,
  source: {
    name: 'Synthetic test source',
    authority: 'Test only',
    url: citation.source_url,
    status: 'verified',
    last_checked_at: time,
    last_successful_check_at: time,
  },
  requirements: [
    {
      id,
      description: 'Synthetic minimum age',
      rule,
      subject_context: 'person',
      citations: [citation],
    },
  ],
  field_evidence: [],
  review_flags: [],
  missing_fields: [],
};
