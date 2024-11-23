Vue.component('admin-dashboard', {
    template: '#admin-dashboard',
    data() {
        return {
            // Add admin-specific data if needed
        };
    }
});

Vue.component('sponsor-dashboard', {
    template: '#sponsor-dashboard',
    data() {
        return {
            campaigns: [] // Fetch campaigns from backend
        };
    },
    created() {
        axios.get('/sponsor/dashboard')
            .then(response => this.campaigns = response.data.campaigns)
            .catch(error => console.error('Error fetching sponsor data:', error));
    }
});

Vue.component('influencer-dashboard', {
    template: '#influencer-dashboard',
    data() {
        return {
            appliedCampaigns: [] // Fetch applied campaigns from backend
        };
    },
    created() {
        axios.get('/influencer/dashboard')
            .then(response => this.appliedCampaigns = response.data.applied_campaigns)
            .catch(error => console.error('Error fetching influencer data:', error));
    }
});

new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data: {
        isLoginVisible: true,
        isRegisterVisible: false,
        loginUsername: '',
        loginPassword: '',
        registerUsername: '',
        registerPassword: '',
        selectedRole: 'influencer', // Default role
        loginError: '',
        registerError: '',
        registerSuccess: '',
        role: '', // To store logged-in user's role
        isLoading: true, // To show a loading state
        campaigns: [], // For sponsor campaigns data
        appliedCampaigns: [], // For influencer campaigns data
    },
    methods: {
        showLoginForm() {
            this.isLoginVisible = true;
            this.isRegisterVisible = false;
            this.clearMessages();
        },
        showRegisterForm() {
            this.isRegisterVisible = true;
            this.isLoginVisible = false;
            this.clearMessages();
        },
        clearMessages() {
            this.loginError = '';
            this.registerError = '';
            this.registerSuccess = '';
        },
        handleLogin() {
            axios.post('/api/login', {
                name: this.loginUsername,
                password: this.loginPassword
            })
            .then(response => {
                if (response.data.success) {
                    this.role = response.data.role[0]; // Assuming the first role is the primary one
                    if (this.role === 'admin') {
                        window.location.href = '/admin/dashboard';
                    } else if (this.role === 'sponsor') {
                        window.location.href = '/sponsor/dashboard';
                    } else if (this.role === 'influencer') {
                        window.location.href = '/influencer/dashboard';
                    }
                } else {
                    this.loginError = response.data.error || 'Login failed.';
                }
            })
            .catch(error => {
                console.error('Login failed:', error);
                this.loginError = error.response?.data?.error || 'An error occurred during login.';
            });
        },
        handleRegister() {
            axios.post('/register', {
                name: this.registerUsername,
                password: this.registerPassword,
                role: this.selectedRole
            })
            .then(response => {
                if (response.data.success) {
                    this.registerSuccess = response.data.message || 'Registration successful!';
                    this.registerError = '';
                } else {
                    this.registerError = response.data.error || 'Registration failed.';
                    this.registerSuccess = '';
                }
            })
            .catch(error => {
                console.error('Registration failed:', error);
                this.registerError = error.response?.data?.error || 'An error occurred during registration.';
                this.registerSuccess = '';
            });
        },
        fetchDashboardData() {
            if (this.role === 'sponsor') {
                axios.get('/sponsor/dashboard')
                    .then(response => this.campaigns = response.data.campaigns)
                    .catch(error => console.error('Error fetching sponsor data:', error));
            } else if (this.role === 'influencer') {
                axios.get('/influencer/dashboard')
                    .then(response => this.appliedCampaigns = response.data.applied_campaigns)
                    .catch(error => console.error('Error fetching influencer data:', error));
            }
        }
    },
    created() {
        // Check if the user is logged in by getting their role
        axios.get('/api/user-role')
            .then(response => {
                if (response.data.role) {
                    this.role = response.data.role; // 'admin', 'sponsor', or 'influencer'
                    this.isLoginVisible = false; // Hide login form if the user is already logged in
                    this.fetchDashboardData(); // Fetch dashboard data based on user role
                } else {
                    this.isLoginVisible = true; // Show login form if not logged in
                }
                this.isLoading = false;
            })
            .catch(error => {
                console.error('Error fetching user role:', error);
                this.isLoginVisible = true; // Show login form if there's an error
                this.isLoading = false;
            });
    }
});
