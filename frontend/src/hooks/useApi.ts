import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

/**
 * axios 인스턴스 — JWT 토큰 자동 첨부 + 401 시 로그아웃 처리
 */
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request 인터셉터: Authorization 헤더에 JWT 토큰 첨부
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response 인터셉터: 401 응답 시 토큰 제거 + 로그인 페이지 리디렉트
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_id");
      localStorage.removeItem("user_role");
      // 로그인 페이지가 존재할 때만 리디렉트
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth API ---

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  role: string;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/api/auth/login", { email, password });
  // 토큰 저장
  localStorage.setItem("access_token", res.data.access_token);
  localStorage.setItem("user_id", String(res.data.user_id));
  localStorage.setItem("user_role", res.data.role);
  return res.data;
}

export async function register(
  email: string,
  password: string,
  name: string,
  role: string = "worker"
): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/api/auth/register", {
    email,
    password,
    name,
    role,
  });
  localStorage.setItem("access_token", res.data.access_token);
  localStorage.setItem("user_id", String(res.data.user_id));
  localStorage.setItem("user_role", res.data.role);
  return res.data;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_id");
  localStorage.removeItem("user_role");
  window.location.href = "/login";
}

export function getStoredAuth() {
  return {
    token: localStorage.getItem("access_token"),
    userId: localStorage.getItem("user_id"),
    role: localStorage.getItem("user_role"),
  };
}

export default api;
