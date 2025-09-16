'use client';

import { useCallback, useMemo, useState, type FormEvent } from 'react';

import { signupFormSchema, type SignupFormData } from '@/lib/validation';

type FormErrors = Partial<Record<keyof SignupFormData, string[]>>;

type FormState = {
  errors: FormErrors;
  formError?: string;
  success?: string;
};

const initialState: FormState = {
  errors: {}
};

export default function SignupPage() {
  const [state, setState] = useState<FormState>(initialState);

  const handleSubmit = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    const values: SignupFormData = {
      name: String(formData.get('name') ?? ''),
      email: String(formData.get('email') ?? ''),
      password: String(formData.get('password') ?? ''),
      confirmPassword: String(formData.get('confirmPassword') ?? '')
    };

    const parsed = signupFormSchema.safeParse(values);

    if (!parsed.success) {
      const { fieldErrors, formErrors } = parsed.error.flatten();
      setState({
        errors: fieldErrors,
        formError: formErrors.length ? formErrors.join(' ') : undefined,
        success: undefined
      });
      return;
    }

    setState({
      errors: {},
      formError: undefined,
      success: 'You have signed up successfully!'
    });

    form.reset();
    const firstField = form.querySelector<HTMLInputElement>('input[name="name"]');
    firstField?.focus();
  }, []);

  const describedBy = useCallback(
    (field: keyof SignupFormData) =>
      state.errors[field]?.length ? `${field}-error` : undefined,
    [state.errors]
  );

  const hasErrors = useMemo(
    () => Object.values(state.errors).some((messages) => (messages?.length ?? 0) > 0),
    [state.errors]
  );

  return (
    <main>
      <form noValidate onSubmit={handleSubmit} aria-describedby={hasErrors ? 'form-errors' : undefined}>
        <h1>Create your account</h1>
        <p className="subtitle">Fill in the form below to sign up for our newsletter and product updates.</p>

        {state.formError ? (
          <div className="message error" role="alert" id="form-errors">
            {state.formError}
          </div>
        ) : null}

        <label htmlFor="name">
          Name
          <input
            type="text"
            id="name"
            name="name"
            autoComplete="name"
            aria-invalid={state.errors.name ? 'true' : 'false'}
            aria-describedby={describedBy('name')}
            required
          />
        </label>
        {state.errors.name ? (
          <div className="message error" role="alert" id="name-error">
            {state.errors.name.map((error, index) => (
              <p key={index}>{error}</p>
            ))}
          </div>
        ) : null}

        <label htmlFor="email">
          Email address
          <input
            type="email"
            id="email"
            name="email"
            autoComplete="email"
            aria-invalid={state.errors.email ? 'true' : 'false'}
            aria-describedby={describedBy('email')}
            required
          />
        </label>
        {state.errors.email ? (
          <div className="message error" role="alert" id="email-error">
            {state.errors.email.map((error, index) => (
              <p key={index}>{error}</p>
            ))}
          </div>
        ) : null}

        <label htmlFor="password">
          Password
          <input
            type="password"
            id="password"
            name="password"
            autoComplete="new-password"
            aria-invalid={state.errors.password ? 'true' : 'false'}
            aria-describedby={describedBy('password')}
            minLength={8}
            required
          />
        </label>
        {state.errors.password ? (
          <div className="message error" role="alert" id="password-error">
            {state.errors.password.map((error, index) => (
              <p key={index}>{error}</p>
            ))}
          </div>
        ) : null}

        <label htmlFor="confirmPassword">
          Confirm password
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            autoComplete="new-password"
            aria-invalid={state.errors.confirmPassword ? 'true' : 'false'}
            aria-describedby={describedBy('confirmPassword')}
            minLength={8}
            required
          />
        </label>
        {state.errors.confirmPassword ? (
          <div className="message error" role="alert" id="confirmPassword-error">
            {state.errors.confirmPassword.map((error, index) => (
              <p key={index}>{error}</p>
            ))}
          </div>
        ) : null}

        <button type="submit">Create account</button>

        {state.success ? (
          <div className="message success" role="status">
            {state.success}
          </div>
        ) : null}
      </form>
    </main>
  );
}
