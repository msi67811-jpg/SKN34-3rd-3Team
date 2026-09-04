import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Profile() {
  const [me, setMe] = useState(null);
  const [biz, setBiz] = useState(null);

  useEffect(() => {
    api.me().then(setMe);
    api.business().then(setBiz);
  }, []);

  if (!me || !biz) return <p>불러오는 중...</p>;

  return (
    <section className="max-w-xl space-y-4">
      <h2 className="text-2xl font-semibold">내 프로필</h2>
      <div className="card p-5 space-y-2 text-sm">
        <p><b>이름</b> {me.name}</p>
        <p><b>이메일</b> {me.email}</p>
        <p><b>나이</b> {me.age || "-"}</p>
        <p><b>지역</b> {me.region || "-"}</p>
        <p><b>사업자 유형</b> {biz.businessType || "-"}</p>
        <p><b>업종</b> {biz.industry || "-"}</p>
        <p><b>창업일</b> {biz.foundedAt || "-"}</p>
      </div>
    </section>
  );
}
