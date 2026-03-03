/**
 * Module overview for frontend/components/StateBlock.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
export function StateBlock({ message }: { message: string }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">{message}</div>;
}
