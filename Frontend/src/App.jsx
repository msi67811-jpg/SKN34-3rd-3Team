import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Chat from "./pages/Chat.jsx";
import Expenses from "./pages/Expenses.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Policies from "./pages/Policies.jsx";
import PolicyDetail from "./pages/PolicyDetail.jsx";
import Profile from "./pages/Profile.jsx";
import Tax from "./pages/Tax.jsx";

function Private({ children }) {
  if (!localStorage.getItem("accessToken")) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <Private>
            <Layout />
          </Private>
        }
      >
        <Route path="/" element={<Home />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/policies/:id" element={<PolicyDetail />} />
        <Route path="/tax" element={<Tax />} />
        <Route path="/expenses" element={<Expenses />} />
        <Route path="/profile" element={<Profile />} />
      </Route>
    </Routes>
  );
}
