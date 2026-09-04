import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function ymd(value) {
  return String(value).slice(0, 10);
}

export default function Home() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [type, setType] = useState("");
  const [events, setEvents] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [policies, setPolicies] = useState([]);

  useEffect(() => {
    api.calendar(year, month, type || undefined).then((d) => setEvents(d.events || []));
  }, [year, month, type]);

  useEffect(() => {
    api.reminders().then((d) => setReminders(d.reminders || []));
    api.recommend().then((d) => setPolicies(d.policies || []));
  }, []);

  const days = useMemo(() => {
    const first = new Date(year, month - 1, 1);
    const start = first.getDay();
    const last = new Date(year, month, 0).getDate();
    const cells = Array.from({ length: start }, () => null);
    for (let d = 1; d <= last; d += 1) cells.push(d);
    return cells;
  }, [year, month]);

  const byDay = {};
  events.forEach((event) => {
    const day = Number(ymd(event.dueDate).slice(8, 10));
    byDay[day] = byDay[day] || [];
    byDay[day].push(event);
  });

  async function addReminder(event) {
    const notifyAt = `${ymd(event.dueDate)}T09:00:00`;
    await api.createReminder({ eventId: event.id, notifyAt });
    const data = await api.reminders();
    setReminders(data.reminders || []);
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">홈 캘린더</h2>
        <p className="text-ink/70">세금 신고일과 지원금 마감일을 한 화면에서 봅니다.</p>
      </header>

      <div className="flex flex-wrap gap-2">
        <select className="rounded-xl border border-sand px-3 py-2" value={year} onChange={(e) => setYear(Number(e.target.value))}>
          <option>2026</option>
          <option>2025</option>
        </select>
        <select className="rounded-xl border border-sand px-3 py-2" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
            <option key={m} value={m}>{m}월</option>
          ))}
        </select>
        <select className="rounded-xl border border-sand px-3 py-2" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">전체</option>
          <option value="tax">세금</option>
          <option value="policy">지원금</option>
        </select>
      </div>

      <div className="card p-4">
        <div className="grid grid-cols-7 gap-2 text-center text-xs text-ink/50">
          {WEEKDAYS.map((d) => <div key={d}>{d}</div>)}
        </div>
        <div className="mt-2 grid grid-cols-7 gap-2">
          {days.map((day, i) => (
            <div key={i} className="min-h-24 rounded-xl bg-paper/70 p-2">
              <p className="text-xs text-ink/50">{day || ""}</p>
              {(byDay[day] || []).map((event) => (
                <button
                  key={event.id}
                  onClick={() => addReminder(event)}
                  className={`mt-1 block w-full truncate rounded-lg px-1 py-0.5 text-left text-[11px] ${
                    event.eventType === "TAX" ? "bg-pine/15 text-pine" : "bg-clay/15 text-clay"
                  }`}
                  title="클릭하면 리마인더 등록"
                >
                  {event.title}
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-5">
          <h3 className="font-semibold">다가오는 알림</h3>
          <ul className="mt-3 space-y-2 text-sm">
            {reminders.map((item) => (
              <li key={item.reminderId} className="flex justify-between gap-2">
                <span>{item.title}</span>
                <span className="text-ink/50">{ymd(item.dueDate)}</span>
              </li>
            ))}
            {!reminders.length && <li className="text-ink/50">등록된 알림이 없습니다.</li>}
          </ul>
        </div>
        <div className="card p-5">
          <h3 className="font-semibold">맞춤 정책 추천</h3>
          <ul className="mt-3 space-y-2 text-sm">
            {policies.slice(0, 4).map((p) => (
              <li key={p.policyId}>
                <Link className="text-pine underline" to={`/policies/${p.policyId}`}>
                  {p.title}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
