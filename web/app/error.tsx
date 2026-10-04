"use client";

export default function ErrorBoundary({
  error,
  reset
}: Readonly<{ error: Error; reset: () => void }>) {
  return (
    <section className="errorPanel" role="alert">
      <h1>Unable to load the workspace</h1>
      <p>{error.message || "The API request could not be completed."}</p>
      <button type="button" className="button" onClick={reset}>
        Try again
      </button>
    </section>
  );
}
