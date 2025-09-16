import { z } from 'zod';

export const signupFormSchema = z
  .object({
    name: z.string().trim().min(1, 'Please enter your name.'),
    email: z.string().trim().email('Please enter a valid email address.'),
    password: z
      .string()
      .min(8, 'Your password must be at least 8 characters long.')
      .regex(/[A-Za-z]/, 'Your password must include a letter.')
      .regex(/\d/, 'Your password must include a number.'),
    confirmPassword: z.string()
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords must match.',
    path: ['confirmPassword']
  });

export type SignupFormData = z.infer<typeof signupFormSchema>;
