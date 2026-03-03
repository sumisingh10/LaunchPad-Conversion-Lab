/**
 * Module overview for frontend/components/LoadingOverlay.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
export function LoadingOverlay({ show, message }: { show: boolean; message: string }) {
  if (!show) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/55 backdrop-blur-sm">
      <div className="rounded-xl bg-white p-6 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-teal-600" />
          <p className="text-sm font-medium text-slate-700">{message}</p>
        </div>
      </div>
    </div>
  );
}
