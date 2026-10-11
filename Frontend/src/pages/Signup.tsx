import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { Radar, Loader2, AlertCircle } from "lucide-react";

type Step = "signup" | "verify";

const Signup = () => {
  const { signUp, verifyOtp, resendOtp, user, loading: authLoading } = useAuth();

  const [step, setStep] = useState<Step>("signup");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Already logged in — redirect to dashboard
  if (!authLoading && user) {
    return <Navigate to="/" replace />;
  }

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setLoading(true);

    const { error: err } = await signUp(email, password);
    setLoading(false);

    if (err) {
      setError(err);
      return;
    }
    setStep("verify");
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setLoading(true);

    const { error: err } = await verifyOtp(email, code.trim());
    setLoading(false);

    if (err) {
      setError(err);
      return;
    }
    // On success, AuthProvider picks up the session and ProtectedRoute
    // will redirect to "/" automatically on the next render.
  };

  const handleResend = async () => {
    setError(null);
    setInfo(null);
    setLoading(true);
    const { error: err } = await resendOtp(email);
    setLoading(false);
    if (err) {
      setError(err);
      return;
    }
    setInfo("We sent a new code to your email.");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <Radar size={24} className="text-primary" />
          <span className="text-lg font-semibold text-foreground">Signal Radar</span>
        </div>

        <div className="border rounded-lg bg-card p-6">
          {step === "signup" ? (
            <>
              <h1 className="text-base font-semibold text-foreground mb-1">
                Create account
              </h1>
              <p className="text-xs text-muted-foreground mb-6">
                Sign up to start tracking signals.
              </p>

              {error && (
                <div className="flex items-start gap-2 p-3 mb-4 rounded bg-destructive/10 text-destructive text-xs">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleSignup} className="space-y-4">
                <div>
                  <label
                    htmlFor="email"
                    className="block text-xs font-medium text-foreground mb-1.5"
                  >
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 text-sm border rounded bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="you@company.com"
                    autoComplete="email"
                  />
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="block text-xs font-medium text-foreground mb-1.5"
                  >
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3 py-2 text-sm border rounded bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="Min 6 characters"
                    autoComplete="new-password"
                    minLength={6}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 px-4 text-sm font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 size={14} className="animate-spin" />}
                  {loading ? "Creating account..." : "Create account"}
                </button>
              </form>
            </>
          ) : (
            <>
              <h1 className="text-base font-semibold text-foreground mb-1">
                Check your email
              </h1>
              <p className="text-xs text-muted-foreground mb-6">
                We sent a 6-digit code to <strong>{email}</strong>. Enter it below to
                activate your account.
              </p>

              {error && (
                <div className="flex items-start gap-2 p-3 mb-4 rounded bg-destructive/10 text-destructive text-xs">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {info && (
                <div className="flex items-start gap-2 p-3 mb-4 rounded bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400 text-xs">
                  <span>{info}</span>
                </div>
              )}

              <form onSubmit={handleVerify} className="space-y-4">
                <div>
                  <label
                    htmlFor="code"
                    className="block text-xs font-medium text-foreground mb-1.5"
                  >
                    Verification code
                  </label>
                  <input
                    id="code"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    required
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                    maxLength={6}
                    minLength={6}
                    className="w-full px-3 py-2 text-sm border rounded bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 tracking-widest text-center font-mono"
                    placeholder="000000"
                    autoComplete="one-time-code"
                    autoFocus
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || code.length !== 6}
                  className="w-full py-2 px-4 text-sm font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 size={14} className="animate-spin" />}
                  {loading ? "Verifying..." : "Verify & log in"}
                </button>
              </form>

              <div className="mt-4 flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setStep("signup");
                    setCode("");
                    setError(null);
                    setInfo(null);
                  }}
                  className="text-muted-foreground hover:text-foreground"
                >
                  Use a different email
                </button>
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={loading}
                  className="text-primary hover:underline disabled:opacity-50"
                >
                  Resend code
                </button>
              </div>
            </>
          )}
        </div>

        <p className="text-center text-xs text-muted-foreground mt-4">
          Already have an account?{" "}
          <Link to="/login" className="text-primary hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Signup;
