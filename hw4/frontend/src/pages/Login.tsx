import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { login } from "../api";
import { useAuth } from "../AuthContext";

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setError("");
    setSubmitting(true);
    try {
      const user = await login(String(data.get("email")), String(data.get("password")));
      setUser(user);
      navigate(from);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page auth">
      <div className="auth-card">
        <p className="eyebrow">Welcome back</p>
        <h1 className="display">Log in</h1>
        <form onSubmit={handleSubmit} className="form">
          <label>
            Email
            <input type="email" name="email" autoComplete="email" required />
          </label>
          <label>
            Password
            <input type="password" name="password" autoComplete="current-password" required />
          </label>
          {error && <p className="notice notice-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn-block" disabled={submitting}>
            {submitting ? "Checking..." : "Log in"}
          </button>
        </form>
        <p className="auth-alt">
          New here? <Link to="/create-account">Create an account</Link>
        </p>
      </div>
    </section>
  );
}
