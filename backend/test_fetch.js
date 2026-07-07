async function test() {
  const loginParams = new URLSearchParams();
  loginParams.append('username', 'testnode@example.com');
  loginParams.append('password', 'password');
  const login = await fetch("http://localhost:8001/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: loginParams
  });
  const data = await login.json();
  const token = data.access_token;
  
  const res = await fetch("http://localhost:8001/generate-recipe", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({ food_name: "Chicken", preferences: "Healthy", use_profile: true })
  });
  
  console.log("Status:", res.status);
  console.log("Body:", await res.text());
}

test();
