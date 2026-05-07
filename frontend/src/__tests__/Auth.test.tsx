import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Auth } from '../components/Auth';
import { BrowserRouter } from 'react-router-dom';

describe('Auth Component', () => {
  it('renders login form by default', () => {
    render(
      <BrowserRouter>
        <Auth />
      </BrowserRouter>
    );
    expect(screen.getByRole('heading', { name: /login/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDefined();
  });

  it('toggles to register form', () => {
    render(
      <BrowserRouter>
        <Auth />
      </BrowserRouter>
    );
    const toggleBtn = screen.getByText(/Need an account\? Register/i);
    fireEvent.click(toggleBtn);

    expect(screen.getByRole('heading', { name: /register/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /sign up/i })).toBeDefined();
  });
});
