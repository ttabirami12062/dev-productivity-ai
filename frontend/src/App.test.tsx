import { render, screen } from '@testing-library/react';
import App from './App';
import { parseRepo } from './api';

vi.mock('axios', () => ({ default: { post: vi.fn(), get: vi.fn(), delete: vi.fn() } }));

test('shows the intro and example repositories before any analysis', () => {
  render(<App />);
  expect(screen.getByText(/weeks before a deadline slips/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'vercel/swr' })).toBeInTheDocument();
});

test('understands repository names and links', () => {
  expect(parseRepo('vercel/swr')).toEqual({ owner: 'vercel', repo: 'swr' });
  expect(parseRepo('https://github.com/vercel/swr.git')).toEqual({ owner: 'vercel', repo: 'swr' });
  expect(parseRepo('github.com/vercel/swr/')).toEqual({ owner: 'vercel', repo: 'swr' });
  expect(parseRepo('just-one-word')).toBeNull();
});
