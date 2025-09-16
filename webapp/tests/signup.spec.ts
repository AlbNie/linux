import { test, expect } from '@playwright/test';

test.describe('Signup page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/signup');
  });

  test('renders the signup form with accessible fields', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
    await expect(page.getByLabel('Name')).toBeVisible();
    await expect(page.getByLabel('Email address')).toHaveAttribute('type', 'email');
    await expect(page.getByLabel('Password')).toHaveAttribute('type', 'password');
    await expect(page.getByLabel('Confirm password')).toHaveAttribute('type', 'password');
  });

  test('shows validation errors when submitting an empty form', async ({ page }) => {
    await page.getByRole('button', { name: 'Create account' }).click();

    await expect(page.locator('#name-error')).toContainText('Please enter your name.');
    await expect(page.locator('#email-error')).toContainText('Please enter a valid email address.');
    await expect(page.locator('#password-error')).toContainText('Your password must be at least 8 characters long.');
    await expect(page.locator('#confirmPassword-error')).toContainText('Passwords must match.');

    await expect(page.getByLabel('Name')).toHaveAttribute('aria-invalid', 'true');
    await expect(page.getByLabel('Email address')).toHaveAttribute('aria-invalid', 'true');
    await expect(page.getByLabel('Password')).toHaveAttribute('aria-invalid', 'true');
    await expect(page.getByLabel('Confirm password')).toHaveAttribute('aria-invalid', 'true');
  });

  test('validates mismatched passwords with an accessible error message', async ({ page }) => {
    await page.getByLabel('Name').fill('Ada Lovelace');
    await page.getByLabel('Email address').fill('ada@example.com');
    await page.getByLabel('Password').fill('Password1');
    await page.getByLabel('Confirm password').fill('Password2');

    await page.getByRole('button', { name: 'Create account' }).click();

    await expect(page.locator('#confirmPassword-error')).toContainText('Passwords must match.');
    await expect(page.getByLabel('Confirm password')).toHaveAttribute('aria-invalid', 'true');
  });

  test('shows a success message when the form is submitted with valid data', async ({ page }) => {
    await page.getByLabel('Name').fill('Grace Hopper');
    await page.getByLabel('Email address').fill('grace@example.com');
    await page.getByLabel('Password').fill('Password1');
    await page.getByLabel('Confirm password').fill('Password1');

    await page.getByRole('button', { name: 'Create account' }).click();

    const successMessage = page.getByRole('status');
    await expect(successMessage).toBeVisible();
    await expect(successMessage).toContainText('You have signed up successfully!');

    await expect(page.getByLabel('Name')).toHaveValue('');
    await expect(page.getByLabel('Email address')).toHaveValue('');
  });
});
