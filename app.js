/**
 * Full-Stack Connectivity Fix
 * Corrects API base paths, headers, and body structures.
 */

// 1. Centralized Base URL configuration
const BASE_URL = "http://127.0.0.1:8001";

/**
 * 4. Validate backend connectivity on script load
 */
console.log("Checking backend connectivity...");
fetch(`${BASE_URL}/health`)
    .then(res => console.log("Backend reachable:", res.status))
    .catch(err => console.error("Backend NOT reachable:", err));

/**
 * Common Response Handler with Detailed Debugging
 */
async function handleResponse(response) {
    // 3. Log response status
    console.log(`Response Status: ${response.status} (${response.url})`);
    
    const data = await response.json();
    if (!response.ok) {
        if (response.status === 401) {
            localStorage.removeItem('token');
            if (!window.location.pathname.includes('login.html')) {
                window.location.href = 'login.html';
            }
        }
        throw new Error(data.detail || "Request failed");
    }
    return data;
}

/**
 * POST /signup - absolute URL + JSON body
 */
async function signupUser(username, password) {
    try {
        const response = await fetch(`${BASE_URL}/signup`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                password
            })
        });
        const data = await handleResponse(response);
        if (data.access_token) localStorage.setItem('token', data.access_token);
        return data;
    } catch (error) {
        // 3. Log errors in console
        console.error("Fetch error (Signup):", error);
        throw error;
    }
}

/**
 * POST /login - absolute URL + JSON body
 */
async function loginUser(username, password) {
    try {
        const response = await fetch(`${BASE_URL}/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                password
            })
        });
        const data = await handleResponse(response);
        if (data.access_token) localStorage.setItem('token', data.access_token);
        return data;
    } catch (error) {
        // 3. Log errors in console
        console.error("Fetch error (Login):", error);
        throw error;
    }
}

/**
 * POST /predict - absolute URL + Authorization header
 */
async function predictStock(ticker) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/predict?ticker=${ticker}`, {
            method: "POST",
            headers: {
                "Authorization": "Bearer " + token
            }
        });
        return await handleResponse(response);
    } catch (error) {
        // 3. Log errors in console
        console.error("Fetch error (Predict):", error);
        if (error.message.includes('Failed to fetch')) {
            throw new Error("Backend not reachable. Ensure server is running at http://127.0.0.1:8000");
        }
        throw error;
    }
}

/**
 * Helper - Redirect non-logged users
 */
function checkAuthStatus() {
    if (!localStorage.getItem('token') && !window.location.pathname.includes('login') && !window.location.pathname.includes('signup')) {
        window.location.href = 'login.html';
    }
}
