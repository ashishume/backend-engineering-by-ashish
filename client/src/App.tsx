import { Routes, Route } from "react-router-dom";
// import Home from "./pages/Home";
import NotFound from "./pages/NotFound";
import Login from "./pages/Login";
import Home from "./pages/Home";
import MultiAgentChat from "./pages/MultiAgentChat";
import NotionAgentChat from "./pages/NotionAgentChat";
// import ProtectedRoute from "./components/ProtectedRoute";
// import Movies from "./pages/Movies";
// import MovieDetails from "./pages/MovieDetails";
// import Theaters from "./pages/Theaters";
// import Showings from "./pages/Showings";
// import Seats from "./pages/Seats";
// import Booking from "./pages/Booking";

function App() {
  return (
    <>
      {/* <Navbar /> */}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Home />} />
        <Route path="/multi-agent-chat" element={<MultiAgentChat />} />
        <Route path="/notion-agent-chat" element={<NotionAgentChat />} />
        {/* <Route
          path="/movies"
          element={
            <ProtectedRoute>
              <Movies />
            </ProtectedRoute>
          }
        />
        <Route
          path="/movies/:movie_id/details"
          element={
            <ProtectedRoute>
              <MovieDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/movies/:movie_id/theaters"
          element={
            <ProtectedRoute>
              <Theaters />
            </ProtectedRoute>
          }
        /> */}
        {/* <Route
          path="/movies/:movie_id/theaters/:theater_id/showings"
          element={
            <ProtectedRoute>
              <Showings />
            </ProtectedRoute>
          }
        /> */}
        {/* <Route
          path="/:theater_id/showings/:showing_id/seats"
          element={
            <ProtectedRoute>
              <Seats />
            </ProtectedRoute>
          }
        />
        <Route
          path="/booking/:showing_id"
          element={
            <ProtectedRoute>
              <Booking />
            </ProtectedRoute>
          }
        /> */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}

export default App;
