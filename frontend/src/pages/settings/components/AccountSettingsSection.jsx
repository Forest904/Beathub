import React from "react";
import SettingsSection from "./SettingsSection.jsx";
import StatusMessage from "./StatusMessage.jsx";

const AccountSettingsSection = ({ sectionsOpen, toggleSection, profile, email, password, userEmail }) => (
  <SettingsSection
    id="profile"
    title="Profile Settings"
    subtitle="Basic details"
    isOpen={sectionsOpen.profile}
    onToggle={toggleSection}
  >
    <form className="space-y-5" onSubmit={profile.onSubmit}>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
          Username
          <input
            type="text"
            name="username"
            value={profile.form.username}
            onChange={profile.onChange}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            placeholder="Your username"
          />
        </label>
        <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
          Date of birth
          <input
            type="date"
            name="dateOfBirth"
            value={profile.dateOfBirth}
            onChange={profile.onDateOfBirthChange}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex flex-1 justify-start">
          <StatusMessage status={profile.status} />
        </div>
        <div className="flex flex-1 justify-end">
          <button
            type="submit"
            className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
          >
            Save changes
          </button>
        </div>
      </div>
    </form>

    <div className="mt-10 space-y-6">
      <SettingsSection
        id="email"
        title="Email"
        subtitle={`Current: ${userEmail}`}
        isOpen={sectionsOpen.email}
        onToggle={toggleSection}
      >
        <form className="space-y-4" onSubmit={email.onSubmit}>
          <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            New email
            <input
              type="email"
              name="newEmail"
              value={email.form.newEmail}
              onChange={email.onChange}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              placeholder="new@email.com"
              required
            />
          </label>

          <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            Current password
            <input
              type="password"
              name="currentPassword"
              value={email.form.currentPassword}
              onChange={email.onChange}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              placeholder="Enter password"
              required
            />
          </label>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex flex-1 justify-start">
              <StatusMessage status={email.status} />
            </div>
            <div className="flex flex-1 justify-end">
              <button
                type="submit"
                className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
              >
                Update email
              </button>
            </div>
          </div>
        </form>
      </SettingsSection>

      <SettingsSection
        id="password"
        title="Password"
        subtitle="Security"
        isOpen={sectionsOpen.password}
        onToggle={toggleSection}
      >
        <form className="space-y-4" onSubmit={password.onSubmit}>
          <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            Current password
            <input
              type="password"
              name="currentPassword"
              value={password.form.currentPassword}
              onChange={password.onChange}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              placeholder="Enter current password"
              required
            />
          </label>

          <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            New password
            <input
              type="password"
              name="newPassword"
              value={password.form.newPassword}
              onChange={password.onChange}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              placeholder="At least 8 characters"
              required
            />
          </label>

          <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            Confirm new password
            <input
              type="password"
              name="confirmPassword"
              value={password.form.confirmPassword}
              onChange={password.onChange}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              placeholder="Repeat new password"
              required
            />
          </label>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex flex-1 justify-start">
              <StatusMessage status={password.status} />
            </div>
            <div className="flex flex-1 justify-end">
              <button
                type="submit"
                className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
              >
                Update password
              </button>
            </div>
          </div>
        </form>
      </SettingsSection>
    </div>
  </SettingsSection>
);

export default AccountSettingsSection;



