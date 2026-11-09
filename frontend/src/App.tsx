import { Navigate, Route, Routes } from "react-router-dom";
import { AccountPage } from "@/domains/auth/components/AccountPage";
import { Dashboard } from "@/domains/auth/components/Dashboard";
import { LoginPage } from "@/domains/auth/components/LoginPage";
import { OAuthCallbackPage } from "@/domains/auth/components/OAuthCallbackPage";
import { RegisterPage } from "@/domains/auth/components/RegisterPage";
import { GuestOnly, RequireAuth, RequireRole } from "@/domains/auth/components/RouteGuards";
import { UsersPage } from "@/domains/auth/components/UsersPage";
import { LandingPage } from "@/domains/landing/components/LandingPage";
import { ProtectedFilesPage } from "@/domains/recovery/components/ProtectedFilesPage";
import { AppLayout } from "@/shared/components/AppLayout";

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={
          <GuestOnly>
            <LoginPage />
          </GuestOnly>
        }
      />
      <Route
        path="/register"
        element={
          <GuestOnly>
            <RegisterPage />
          </GuestOnly>
        }
      />
      <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/files" element={<ProtectedFilesPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route
          path="/users"
          element={
            <RequireRole role="admin">
              <UsersPage />
            </RequireRole>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
