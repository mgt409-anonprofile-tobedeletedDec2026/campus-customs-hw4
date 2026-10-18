import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PASSWORD_RULES, signup } from "../api";
import { useAuth } from "../AuthContext";

export default function CreateAccount() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const allRulesMet = PASSWORD_RULES.every((r) => r.test(password));
  const mismatch = confirm.length > 0 && confirm !== password;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!allRulesMet) {
      setError("Please choose a password that meets every requirement below.");
      return;
    }
    if (password !== confirm) {
      setError("Those passwords don't match.");
      return;
    }
    const data = new FormData(e.currentTarget);
    setError("");
    setSubmitting(true);
    try {
      const user = await signup({
        first_name: String(data.get("first_name")),
        last_name: String(data.get("last_name")),
        email: String(data.get("email")),
        password,
        confirm_password: confirm,
      });
      setUser(user);
      navigate("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page auth">
      <div className="auth-card">
        <p className="eyebrow">Join the ledger</p>
        <h1 className="display">Create account</h1>
        <form onSubmit={handleSubmit} className="form">
          <div className="form-row">
            <label>
              First name
              <input name="first_name" autoComplete="given-name" maxLength={60} required />
            </label>
            <label>
              Last name
              <input name="last_name" autoComplete="family-name" maxLength={60} required />
            </label>
          </div>
          <label>
            Email
            <input type="email" name="email" autoComplete="email" required />
          </label>
          <label>
            Password
            <input
              type="password"
              name="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-describedby="password-rules"
              required
            />
          </label>
          <ul id="password-rules" className="pw-rules" aria-label="Password requirements">
            {PASSWORD_RULES.map((r) => {
              const met = r.test(password);
              return (
                <li key={r.label} className={met ? "is-met" : ""}>
                  <span aria-hidden="true">{met ? "✓" : "○"}</span> {r.label}
                  <span className="sr-only">{met ? " (done)" : " (not yet)"}</span>
                </li>
              );
            })}
          </ul>
          <label>
            Confirm password
            <input
              type="password"
              name="confirm"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
            {mismatch && <span className="hint hint-error">Passwords don&rsquo;t match yet.</span>}
          </label>
          {error && <p className="notice notice-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn-block" disabled={submitting}>
            {submitting ? "Creating..." : "Create account"}
          </button>
        </form>
        <p className="auth-alt">
          Already have one? <Link to="/login">Log in</Link>
        </p>
      </div>
    </section>
  );
}
