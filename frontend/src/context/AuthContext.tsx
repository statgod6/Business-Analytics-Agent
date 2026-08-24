import {
  createContext,
  useCallback,
  useEffect,
  useReducer,
  type ReactNode,
} from "react";
import type { User } from "../types";
import { setToken, clearToken, getToken } from "../api/client";
import * as authApi from "../api/auth";

/* ── State ─────────────────────────────────────────────── */

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

type AuthAction =
  | { type: "LOADING" }
  | { type: "LOGIN_SUCCESS"; token: string }
  | { type: "SET_USER"; user: User }
  | { type: "ERROR"; error: string }
  | { type: "LOGOUT" };

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "LOADING":
      return { ...state, isLoading: true, error: null };
    case "LOGIN_SUCCESS":
      return { ...state, token: action.token, isLoading: false, error: null };
    case "SET_USER":
      return { ...state, user: action.user, isLoading: false };
    case "ERROR":
      return { ...state, isLoading: false, error: action.error };
    case "LOGOUT":
      return { user: null, token: null, isLoading: false, error: null };
    default:
      return state;
  }
}

const initialState: AuthState = {
  user: null,
  token: getToken(),
  isLoading: true,
  error: null,
};

/* ── Context ───────────────────────────────────────────── */

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

/* ── Provider ──────────────────────────────────────────── */

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Validate stored token on mount
  useEffect(() => {
    if (!state.token) {
      dispatch({ type: "SET_USER", user: null as unknown as User });
      return;
    }
    authApi
      .getMe()
      .then((user) => dispatch({ type: "SET_USER", user }))
      .catch(() => {
        clearToken();
        dispatch({ type: "LOGOUT" });
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async (email: string, password: string) => {
    dispatch({ type: "LOADING" });
    try {
      const res = await authApi.login(email, password);
      setToken(res.access_token);
      dispatch({ type: "LOGIN_SUCCESS", token: res.access_token });
      const user = await authApi.getMe();
      dispatch({ type: "SET_USER", user });
    } catch (err) {
      dispatch({
        type: "ERROR",
        error: err instanceof Error ? err.message : "Login failed",
      });
      throw err;
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    dispatch({ type: "LOADING" });
    try {
      await authApi.register(email, password);
      // Auto-login after registration
      await login(email, password);
    } catch (err) {
      dispatch({
        type: "ERROR",
        error: err instanceof Error ? err.message : "Registration failed",
      });
      throw err;
    }
  }, [login]);

  const logout = useCallback(() => {
    clearToken();
    dispatch({ type: "LOGOUT" });
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}