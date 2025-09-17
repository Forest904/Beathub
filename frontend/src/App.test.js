import { render, screen } from '@testing-library/react';
import App from './App';

test('renders primary navigation links', () => {
  render(<App />);
  expect(screen.getByRole('link', { name: /cd burner/i })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /artists/i })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /download/i })).toBeInTheDocument();
});
