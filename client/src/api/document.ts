import axios from "axios";
// Use environment variable if set, otherwise use relative URL through nginx
const DOCUMENT_BASE_URL = import.meta.env.VITE_DOCUMENT_API_URL || "/documents";

const documentApi = axios.create({
  baseURL: DOCUMENT_BASE_URL,
  withCredentials: true, // Enable sending cookies with requests
});

const getWorkspaces = async () => {
  const response = await documentApi.get("/workspaces");
  return response.data;
};

export { getWorkspaces };
