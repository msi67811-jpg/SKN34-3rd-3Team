import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";

export default function PolicyDetail() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [elig, setElig] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.policy(id).then(setDetail);
    api.eligibility(id).then(setElig);
  }, [id]);

  if (!detail) return <p>불러오는 중...</p>;
  const p = detail.policy;

  return (
    <section className="max-w-2xl space-y-5">
      <p className="text-sm text-moss">{p.region} · {p.source}</p>
      <h2 className="text-2xl font-semibold">{p.title}</h2>
      <div className="card space-y-2 p-5 text-sm">
        <p><b>대상</b> {p.target}</p>
        <p><b>혜택</b> {p.benefit}</p>
        <p><b>신청기간</b> {detail.applyPeriod}</p>
        <p><b>신청방법</b> {detail.applyMethod}</p>
      </div>
      {elig && (
        <div className="card p-5">
          <h3 className="font-semibold">{elig.eligible ? "자격 충족 가능성이 있습니다" : "지금 프로필 기준으로는 미충족"}</h3>
          <ul className="mt-2 list-disc pl-5 text-sm text-ink/70">
            {elig.reasons.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      )}
      <button
        className="rounded-xl bg-pine px-4 py-2 text-white"
        onClick={async () => {
          await api.savePolicy(id);
          setSaved(true);
        }}
      >
        {saved ? "관심 정책에 저장됨" : "관심 정책 저장"}
      </button>
    </section>
  );
}
