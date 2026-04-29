import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Navbar() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const onLogoutHandler = async () => {
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <nav className="bg-blue-600 text-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="text-xl font-bold hover:text-blue-200">
            FastAPI Learning
          </Link>
          <div className="flex space-x-6">
            {/* <Link
              to="/movies"
              className="hover:text-blue-200 transition-colors"
            >
              Movies
            </Link> */}
            {/* <Link to="/about" className="hover:text-blue-200 transition-colors">
              About
            </Link> */}
            {/* <select disabled>
              {workspaces?.workspaces?.map((workspace: any) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select> */}
            <button onClick={onLogoutHandler}>Logout</button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
