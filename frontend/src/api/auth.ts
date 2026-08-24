import { api } from "./client";
import type { TokenOut, User, UserRegister } from "../types";

export async function register(email: string, password: string): Promise<User> {
  return api.post<User>("/auth/register", { email, password } as UserRegister);
}

export async function login(email: string, password: string): Promise<TokenOut> {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const res = await fetch("/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData,
  });

  if (!res.ok) {
    const detail = res.status === 401 ? "Invalid email or password" : res.statusText;
    throw new Error(detail);
  }

  return res.json();
}

export async function getMe(): Promise<User> {
  return api.get<User>("/auth/me");
}