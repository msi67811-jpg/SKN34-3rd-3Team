import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];
const field = "rounded-xl border border-[#d8d0c0] bg-white px-3 py-2";

function ymd(value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const y = value.getFullYear();
    const m = String(value.getMonth() + 1).padStart(2, "0");
    const d = String(value.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }
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
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState(ymd(today));
  const [description, setDescription] = useState("");
  const [notifyTime, setNotifyTime] = useState("09:00");
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);
  const [phoneSaved, setPhoneSaved] = useState("");

  async function reloadCalendar() {
    const data = await api.calendar(year, month, type || undefined);
    setEvents(data.events || []);
  }

  async function reloadReminders() {
    const data = await api.reminders();
    setReminders(data.reminders || []);
  }

  useEffect(() => {
    reloadCalendar();
  }, [year, month, type]);

  useEffect(() => {
    reloadReminders();
    api.recommend().then((d) => setPolicies(d.policies || []));
    api.me().then((me) => setPhone(me.phone || "")).catch(() => {});
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

  function notifyAtFor(dateValue) {
    return `${ymd(dateValue)}T${notifyTime}:00`;
  }

  async function addReminder(event) {
    try {
      await api.createReminder({ eventId: event.id, notifyAt: notifyAtFor(event.dueDate) });
      await reloadReminders();
    } catch (err) {
      window.alert(err.message);
    }
  }

  async function savePhone(e) {
    e.preventDefault();
    const value = phone.trim();
    if (!value) {
      window.alert("휴대폰 번호를 입력하세요.");
      return;
    }
    try {
      await api.updateMe({ phone: value });
      setPhoneSaved("번호가 저장되었습니다. 알림 시각에 알림함·브라우저 알림·문자 대기로 갑니다.");
    } catch (err) {
      window.alert(err.message);
    }
  }

  async function addEvent(e) {
    e.preventDefault();
    if (!title.trim() || !dueDate) return;
    setSaving(true);
    try {
      await api.createEvent({
        title: title.trim(),
        dueDate,
        description,
        notifyAt: notifyAtFor(dueDate),
      });
      const due = new Date(`${dueDate}T00:00:00`);
      const nextYear = due.getFullYear();
      const nextMonth = due.getMonth() + 1;
      setYear(nextYear);
      setMonth(nextMonth);
      setTitle("");
      setDescription("");
      const cal = await api.calendar(nextYear, nextMonth, type || undefined);
      setEvents(cal.events || []);
      await reloadReminders();
    } catch (err) {
      window.alert(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function removeEvent(event, e) {
    e.stopPropagation();
    if (!window.confirm(`「${event.title}」 일정을 삭제할까요?`)) return;
    try {
      await api.deleteEvent(event.id);
      await reloadCalendar();
      await reloadReminders();
    } catch (err) {
      window.alert(err.message);
    }
  }

  function pickDay(day) {
    if (!day) return;
    const value = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    setDueDate(value);
  }

  function eventClass(event) {
    if (event.eventType === "TAX") return "bg-[#d9efe6] text-[#1f6b4f]";
    if (event.eventType === "USER") return "bg-[#e4eaf7] text-[#2c4a7c]";
    return "bg-[#f4e3c2] text-[#8a5a12]";
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">홈 캘린더</h2>
        <p className="text-neutral-500">
          휴대폰 번호와 알림 시각을 정한 뒤 일정을 등록하면, 그 날짜·시각에 알림이 갑니다.
        </p>
      </header>

      <form className="ui-card flex flex-wrap items-end gap-2 p-4" onSubmit={savePhone}>
        <label className="grid gap-1 text-sm">
          <span className="text-neutral-500">휴대폰 번호</span>
          <input
            className={field}
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="010-1234-5678"
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-neutral-500">알림 시각</span>
          <input className={field} type="time" value={notifyTime} onChange={(e) => setNotifyTime(e.target.value)} />
        </label>
        <button className="rounded-xl bg-[#1f6b4f] px-4 py-2 text-white" type="submit">
          번호 저장
        </button>
        {phoneSaved && <p className="w-full text-sm text-[#1f6b4f]">{phoneSaved}</p>}
      </form>

      <form className="ui-card flex flex-wrap items-end gap-2 p-4" onSubmit={addEvent}>
        <label className="grid gap-1 text-sm">
          <span className="text-neutral-500">내 일정</span>
          <input className={field} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 세무사 상담" required />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-neutral-500">날짜</span>
          <input className={field} type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
        </label>
        <label className="grid min-w-48 flex-1 gap-1 text-sm">
          <span className="text-neutral-500">메모</span>
          <input className={field} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="선택" />
        </label>
        <button className="rounded-xl bg-[#1f6b4f] px-4 py-2 text-white" disabled={saving} type="submit">
          {saving ? "저장 중" : "등록"}
        </button>
      </form>

      <div className="flex flex-wrap gap-2">
        <select className={field} value={year} onChange={(e) => setYear(Number(e.target.value))}>
          <option>2026</option>
          <option>2025</option>
        </select>
        <select className={field} value={month} onChange={(e) => setMonth(Number(e.target.value))}>
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
            <option key={m} value={m}>{m}월</option>
          ))}
        </select>
        <select className={field} value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">전체</option>
          <option value="tax">세금</option>
          <option value="policy">지원금</option>
          <option value="user">내 일정</option>
        </select>
      </div>

      <div className="ui-card p-4">
        <div className="grid grid-cols-7 gap-2 text-center text-xs text-neutral-500">
          {WEEKDAYS.map((d) => <div key={d}>{d}</div>)}
        </div>
        <div className="mt-2 grid grid-cols-7 gap-2">
          {days.map((day, i) => (
            <div
              key={i}
              className="min-h-24 cursor-pointer rounded-xl bg-[#f6f1e8] p-2"
              onClick={() => pickDay(day)}
            >
              <p className="text-xs text-neutral-400">{day || ""}</p>
              {(byDay[day] || []).map((event) => (
                <div key={event.id} className="mt-1 flex items-stretch gap-1">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      addReminder(event);
                    }}
                    className={`block min-w-0 flex-1 truncate rounded-lg px-1 py-0.5 text-left text-[11px] ${eventClass(event)}`}
                    title="클릭하면 선택한 시각으로 알림 등록"
                  >
                    {event.title}
                  </button>
                  {event.mine && (
                    <button
                      type="button"
                      className="rounded-lg px-1 text-[11px] text-rose-600"
                      title="내 일정 삭제"
                      onClick={(e) => removeEvent(event, e)}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="ui-card p-5">
          <h3 className="font-semibold">다가오는 알림</h3>
          <ul className="mt-3 space-y-2 text-sm">
            {reminders.map((item) => (
              <li key={item.reminderId} className="flex items-start justify-between gap-2">
                <span>
                  {item.title}
                  {item.arrived && <span className="ml-2 text-amber-300">알림 도착</span>}
                  {item.dueSoon && !item.arrived && <span className="ml-2 text-cyan-300">마감 임박</span>}
                </span>
                <span className="flex items-center gap-2 text-slate-500">
                  {ymd(item.dueDate)} {String(item.notifyAt || "").slice(11, 16)}
                  <button
                    className="text-[#1f6b4f] underline"
                    onClick={async () => {
                      await api.pushNotification(item.eventId);
                      window.alert("알림함과 메일 대기열에 넣었습니다.");
                    }}
                  >
                    지금 알림
                  </button>
                  <button
                    className="text-rose-600 underline"
                    onClick={async () => {
                      await api.deleteReminder(item.reminderId);
                      await reloadReminders();
                    }}
                  >
                    삭제
                  </button>
                </span>
              </li>
            ))}
            {!reminders.length && <li className="text-slate-500">등록된 알림이 없습니다.</li>}
          </ul>
        </div>
        <div className="ui-card p-5">
          <h3 className="font-semibold">맞춤 정책 추천</h3>
          <ul className="mt-3 space-y-2 text-sm">
            {policies.slice(0, 4).map((p) => (
              <li key={p.policyId}>
                <Link className="text-[#1f6b4f] underline" to={`/policies/${p.policyId}`}>
                  {p.title}
                </Link>
                {p.matchScore != null && (
                  <span className="ml-2 text-xs font-medium text-black">{p.matchScore}점</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
