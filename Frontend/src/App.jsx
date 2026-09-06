import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import AdminLayout from "./pages/admin/AdminLayout.jsx";
import AdminDashboard from "./pages/admin/AdminDashboard.jsx";
import AdminDocuments from "./pages/admin/AdminDocuments.jsx";
import AdminLogin from "./pages/admin/AdminLogin.jsx";
import AdminUsers from "./pages/admin/AdminUsers.jsx";
import Chat from "./pages/Chat.jsx";
import Expenses from "./pages/Expenses.jsx";
import Home from "./pages/Home.jsx";
import LlmLabPage from "./pages/LlmLab.jsx";
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
  if (localStorage.getItem("userRole") === "admin") {
    return <Navigate to="/admin" replace />;
  }
  return children;
}

function AdminPrivate({ children }) {
  if (!localStorage.getItem("accessToken") || localStorage.getItem("userRole") !== "admin") {
    return <Navigate to="/admin/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route
          path="/admin"
          element={
            <AdminPrivate>
              <AdminLayout />
            </AdminPrivate>
          }
        >
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="documents" element={<AdminDocuments />} />
        </Route>
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
          <Route path="/llm-lab" element={<LlmLabPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
