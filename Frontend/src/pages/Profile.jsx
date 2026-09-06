import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Profile() {
  const [me, setMe] = useState(null);
  const [biz, setBiz] = useState(null);

  useEffect(() => {
    Promise.all([api.me(), api.business()]).then(([user, business]) => {
      setMe(user);
      setBiz(business);
    });
  }, []);

  if (!me) {
    return <p className="text-slate-400">불러오는 중...</p>;
  }

  return (
    <section className="max-w-2xl space-y-4">
      <h2 className="text-2xl font-semibold">내 프로필</h2>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-white">
        <p>
          <span className="text-white">이름</span> {me.name}
        </p>
        <p className="mt-2">
          <span className="text-white">이메일</span> {me.email}
        </p>
        <p className="mt-2">
          <span className="text-white">나이</span> {me.age}
        </p>
        <p className="mt-2">
          <span className="text-white">지역</span> {me.region}
        </p>
        <p className="mt-2">
          <span className="text-white">휴대폰</span> {me.phone || "-"}
        </p>
      </div>
      {biz && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-white">
          <h3 className="mb-3 font-semibold text-white">사업자 정보</h3>
          <p>
            <span className="text-white">유형</span> {biz.businessType}
          </p>
          <p className="mt-2">
            <span className="text-white">업종</span> {biz.industry}
          </p>
          <p className="mt-2">
            <span className="text-white">창업일</span> {String(biz.foundedAt || "").slice(0, 10)}
          </p>
          <p className="mt-2">
            <span className="text-white">사업자등록일</span>{" "}
            {String(biz.businessRegisteredAt || "").slice(0, 10)}
          </p>
        </div>
      )}
    </section>
  );
}
