import { useEffect, useState } from "react";
import { api } from "../../api.js";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    const data = await api.adminUsers();
    setUsers(data.users || []);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  async function openDetail(id) {
    try {
      setDetail(await api.adminUser(id));
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleStatus(user) {
    const next = user.status === "suspended" ? "active" : "suspended";
    try {
      await api.adminUpdateUser(user.id, { status: next });
      await load();
      if (detail?.user?.id === user.id) {
        await openDetail(user.id);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">사용자 관리</h2>
        <p className="text-slate-400">회원 목록을 보고 활성/정지를 바꿀 수 있습니다.</p>
      </header>

      <ul className="space-y-2">
        {users.map((user) => (
          <li
            key={user.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-3"
          >
            <button className="text-left" onClick={() => openDetail(user.id)}>
              <p className="font-medium text-slate-100">{user.name}</p>
              <p className="text-xs text-slate-500">
                {user.email} · {user.region || "지역 미입력"} · {user.status}
              </p>
            </button>
            <button className="text-sm text-amber-300 underline" onClick={() => toggleStatus(user)}>
              {user.status === "suspended" ? "활성화" : "정지"}
            </button>
          </li>
        ))}
        {!users.length && <li className="text-slate-500">등록된 사용자가 없습니다.</li>}
      </ul>

      {detail && (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 text-sm text-slate-300">
          <h3 className="font-semibold text-slate-100">{detail.user.name} 상세</h3>
          <p className="mt-2">{detail.user.email}</p>
          <p className="mt-1">
            {detail.user.age || "-"}세 · {detail.user.region || "-"} · {detail.user.status}
          </p>
          <p className="mt-1">
            사업자 {detail.user.business?.businessType || "-"} / {detail.user.business?.industry || "-"}
          </p>
          <p className="mt-3 text-slate-500">
            상담 {detail.usage?.chatMessages || 0} · 지출 {detail.usage?.expenses || 0} · 관심정책{" "}
            {detail.usage?.savedPolicies || 0}
          </p>
        </div>
      )}
      {error && <p className="text-sm text-rose-300">{error}</p>}
    </section>
  );
}
