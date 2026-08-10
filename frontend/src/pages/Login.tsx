import { useState } from "react";
import { login } from "../hooks/useApi";

interface LoginProps {
  onLoginSuccess: () => void;
}

export default function Login({ onLoginSuccess }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      onLoginSuccess();
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || "로그인에 실패했습니다");
      } else {
        setError("서버에 연결할 수 없습니다");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-center text-red-600 mb-2">
          FireEscape AI
        </h1>
        <p className="text-center text-gray-500 mb-6 text-sm">
          위치 기반 실시간 탈출 경로 시스템
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              이메일
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
              placeholder="admin@fire.io"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              비밀번호
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
              placeholder="demo1234"
              required
            />
          </div>

          {error && (
            <p className="text-red-600 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-red-600 text-white rounded-md font-medium hover:bg-red-700 transition disabled:opacity-50"
          >
            {loading ? "로그인 중..." : "로그인"}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t">
          <p className="text-xs text-gray-400 text-center mb-2">데모 계정</p>
          <div className="text-xs text-gray-500 space-y-1">
            <p><span className="font-medium">관리자:</span> admin@fire.io / demo1234</p>
            <p><span className="font-medium">구조대:</span> rescuer@fire.io / demo1234</p>
            <p><span className="font-medium">근로자1:</span> worker1@fire.io / demo1234</p>
            <p><span className="font-medium">근로자2:</span> worker2@fire.io / demo1234</p>
          </div>
        </div>
      </div>
    </div>
  );
}
