import Link from 'next/link';

export default function HomePage() {
  return (
    <main>
      <form aria-labelledby="home-title" role="presentation">
        <h1 id="home-title">Welcome</h1>
        <p className="subtitle">
          This demo showcases an accessible sign up form powered by Next.js, Zod, and Playwright tests.
        </p>
        <Link href="/signup" className="message success" style={{ textAlign: 'center', textDecoration: 'none' }}>
          Go to the sign up form
        </Link>
      </form>
    </main>
  );
}
