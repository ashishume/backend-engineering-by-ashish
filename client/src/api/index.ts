import axios from "axios";
import type { BookingSeat, LockedSeat } from "./models";

// Use environment variables if set, otherwise use relative URLs through nginx
const AUTH_BASE_URL = import.meta.env.VITE_AUTH_API_URL || "/auth";
const BOOKING_BASE_URL = import.meta.env.VITE_BOOKING_API_URL || "/booking";

const authApi = axios.create({
  baseURL: AUTH_BASE_URL,
  withCredentials: true, // Enable sending cookies with requests
});

const bookingApi = axios.create({
  baseURL: BOOKING_BASE_URL,
  withCredentials: true, // Enable sending cookies with requests
});

// Add response interceptor to handle authentication errors globally
const setupInterceptor = (logoutCallback: () => void) => {
  const interceptor = (error: any) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - clear user state
      logoutCallback();
    }
    return Promise.reject(error);
  };

  authApi.interceptors.response.use((response) => response, interceptor);
  bookingApi.interceptors.response.use((response) => response, interceptor);
};

const login = async (email: string, password: string) => {
  const response = await authApi.post("/login", { email, password });
  return response.data;
};

const signup = async (email: string, password: string) => {
  const response = await authApi.post("/signup", { email, password });
  return response.data;
};

const getMovies = async () => {
  const response = await bookingApi.get("/movies");
  return response.data;
};

const getMovieById = async (movie_id: string) => {
  const response = await bookingApi.get(`/movies/${movie_id}`);
  return response.data;
};

const getTheaters = async () => {
  const response = await bookingApi.get(`/theaters`);
  return response.data;
};

const getShowings = async (theater_id: string, movie_id: string) => {
  const response = await bookingApi.get(`/showings/${theater_id}/${movie_id}`);
  return response.data;
};

const getSeats = async (theater_id: string) => {
  const response = await bookingApi.get(`/seats/${theater_id}`);
  return response.data;
};

const getBookingSeats = async (
  showing_id: string
): Promise<{
  booked_seats: BookingSeat[];
  locked_seats: LockedSeat[];
}> => {
  const response = await bookingApi.get(`/booking_seats/${showing_id}`);
  return response.data;
};
const createBooking = async (booking: {
  showing_id: string;
  seats_ids: string[];
  total_price: number;
}) => {
  const response = await bookingApi.post(`/bookings`, booking);
  return response.data;
};

const getUserDetails = async () => {
  const response = await authApi.get(`/user_details`);
  return response.data;
};

const createBookingLock = async (booking_lock: {
  showing_id: string;
  seat_id: string;
  lock_seat: boolean;
}) => {
  const response = await bookingApi.post(`/booking_seats/lock`, booking_lock);
  return response.data;
};

export {
  authApi,
  bookingApi,
  setupInterceptor,
  login,
  signup,
  getMovies,
  getMovieById,
  createBookingLock,
  getTheaters,
  getSeats,
  getShowings,
  createBooking,
  getBookingSeats,
  getUserDetails,
};
