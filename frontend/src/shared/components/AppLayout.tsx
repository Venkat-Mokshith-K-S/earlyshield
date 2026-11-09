import { Outlet } from "react-router-dom";
import { TopStatusBar } from "@/shared/components/TopStatusBar";

/** Header + navigation shared by every signed-in page; the page renders into <Outlet />. */
export function AppLayout() {
  return (
    <div className="min-h-screen bg-surface-950">
      <TopStatusBar />
      <Outlet />
    </div>
  );
}
