import { createContext, useContext, useState, useEffect, useCallback } from "react"
import axios from "axios"

const AuthContext = createContext(null)

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem("auth_token"))
  const [loading, setLoading] = useState(true)
  const [industries, setIndustries] = useState([])

  // Define logout function before it's used
  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    localStorage.removeItem("auth_token")
    delete axios.defaults.headers.common["Authorization"]
  }, [])

  // Configure axios defaults
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`
    } else {
      delete axios.defaults.headers.common["Authorization"]
    }
  }, [token])

  // Load user on mount if token exists
  useEffect(() => {
    const loadUser = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API_BASE_URL}/auth/me`)
          if (response.data.success) {
            setUser(response.data.user)
          } else {
            // Invalid token, clear it
            logout()
          }
        } catch (error) {
          console.error("Error loading user:", error)
          logout()
        }
      }
      setLoading(false)
    }

    loadUser()
  }, [token, logout])

  // Load industries on mount
  useEffect(() => {
    const loadIndustries = async () => {
      try {
        console.log("Loading industries from:", `${API_BASE_URL}/industries`)
        const response = await axios.get(`${API_BASE_URL}/industries`)
        console.log("Industries response:", response.data)
        if (response.data && Array.isArray(response.data)) {
          setIndustries(response.data)
        } else {
          console.error("Invalid industries response:", response.data)
        }
      } catch (error) {
        console.error("Error loading industries:", error)
        console.error("Error details:", error.response?.data || error.message)
      }
    }

    loadIndustries()
  }, [])

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, {
        email,
        password,
      })

      if (response.data.success) {
        const { access_token, user: userData } = response.data
        setToken(access_token)
        setUser(userData)
        localStorage.setItem("auth_token", access_token)
        axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`
        return { success: true }
      } else {
        return { success: false, error: response.data.message || "Login failed" }
      }
    } catch (error) {
      const errorMessage =
        error.response?.data?.detail || error.message || "Login failed"
      return { success: false, error: errorMessage }
    }
  }

  const signup = async (email, password, industry, name, company) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/signup`, {
        email,
        password,
        industry,
        name,
        company,
      })

      if (response.data.success) {
        const { access_token, user: userData } = response.data
        setToken(access_token)
        setUser(userData)
        localStorage.setItem("auth_token", access_token)
        axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`
        return { success: true }
      } else {
        return { success: false, error: response.data.message || "Signup failed" }
      }
    } catch (error) {
      const errorMessage =
        error.response?.data?.detail || error.message || "Signup failed"
      return { success: false, error: errorMessage }
    }
  }

  const value = {
    user,
    token,
    loading,
    industries,
    login,
    signup,
    logout,
    isAuthenticated: !!user && !!token,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

