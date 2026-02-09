'use client';

import { createContext } from 'react';

interface AuthContextType {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<string>;
  logout: () => void;
  user: null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export const AuthContext = createContext<AuthContextType>({
  login: async () => {},
  register: async () => '',
  logout: () => {},
  user: null,
  isAuthenticated: false,
  isLoading: false,
});
