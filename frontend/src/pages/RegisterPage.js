import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../shared/hooks/useAuth';

const RegisterPage = () => {
  const navigate = useNavigate();
  const { register, errors, clearErrors } = useAuth();
  const [form, setForm] = useState({ email: '', password: '', confirmPassword: '' });
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
    if (errors) {
      clearErrors();
    }
  };

  const validate = () => {
    const nextErrors = {};
    if (!form.email) {
      nextErrors.email = 'Email is required.';
    }
    if (!form.password || form.password.length < 8) {
      nextErrors.password = 'Password must be at least 8 characters long.';
    }
    if (form.password !== form.confirmPassword) {
      nextErrors.confirmPassword = 'Passwords do not match.';
    }
    setFieldErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitting) return;
    if (!validate()) return;
    setSubmitting(true);
    const result = await register({ email: form.email, password: form.password });
    setSubmitting(false);
    if (result.ok) {
      navigate('/settings', { state: { focus: 'apiKeys' } });
    }
  };

  const mergedErrors = { ...fieldErrors, ...(errors || {}) };

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-md flex-col justify-center px-4 py-12">
      <h1 className="text-3xl font-semibold text-slate-900 dark:text-slate-100">Join BeatHub</h1>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-brand-600 hover:text-brand-500 dark:text-brandDark-200">
          Sign in
        </Link>
      </p>
      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        {mergedErrors.form && (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-500/40 dark:bg-red-900/30 dark:text-red-100">
            {mergedErrors.form}
          </div>
        )}
        <div className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
              Email address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              value={form.email}
              onChange={handleChange}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            {mergedErrors.email && <p className="mt-1 text-sm text-red-600 dark:text-red-300">{mergedErrors.email}</p>}
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              value={form.password}
              onChange={handleChange}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            {mergedErrors.password && <p className="mt-1 text-sm text-red-600 dark:text-red-300">{mergedErrors.password}</p>}
          </div>
          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 dark:text-slate-200">
              Confirm password
            </label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              value={form.confirmPassword}
              onChange={handleChange}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            {mergedErrors.confirmPassword && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-300">{mergedErrors.confirmPassword}</p>
            )}
          </div>
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-70 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
        >
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </div>
  );
};

export default RegisterPage;
