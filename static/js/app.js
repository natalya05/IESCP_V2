// Admin Dashboard Component
Vue.component('admin-dashboard', {
    template: '#admin-dashboard',
    data() {
        return {
            // Add admin-specific data if needed
        };
    },
    methods: {
        logout() {
            this.$root.logout(); // Use root's logout method
        }
    }
});

// Sponsor Dashboard Component
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
    },
    methods: {
        logout() {
            this.$root.logout(); // Use root's logout method
        }
    }
});

// Influencer Dashboard Component
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
    },
    methods: {
        logout() {
            this.$root.logout(); // Use root's logout method
        }
    }
});

// Main Vue Instance
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
                    this.isLoginVisible = false; // Hide login form
                    this.fetchDashboardData(); // Load dashboard data
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
        },
        logout() {
            axios.post('/api/logout')
                .then(response => {
                    if (response.data.success) {
                        // Reset Vue instance state
                        this.isLoginVisible = true;
                        this.isRegisterVisible = false;
                        this.loginUsername = '';
                        this.loginPassword = '';
                        this.registerUsername = '';
                        this.registerPassword = '';
                        this.selectedRole = 'influencer'; // Reset role
                        this.loginError = '';
                        this.registerError = '';
                        this.registerSuccess = '';
                        this.role = '';
                        this.campaigns = [];
                        this.appliedCampaigns = [];
                        window.location.href = '/'; // Redirect to home page
                    } else {
                        console.error('Logout failed:', response.data.message);
                    }
                })
                .catch(error => {
                    console.error('Logout request failed:', error);
                });
        }
    },
    created() {
        axios.get('/api/user-role')
            .then(response => {
                if (response.data.role) {
                    this.role = response.data.role; // Valid user role
                    this.isLoginVisible = false; // Hide login form
                    this.fetchDashboardData();
                } else {
                    this.role = ''; // No role found
                    this.isLoginVisible = true; // Show login form
                }
                this.isLoading = false;
            })
            .catch(error => {
                console.error('Error fetching user role:', error);
                this.role = ''; // Reset role on error
                this.isLoginVisible = true; // Ensure login form is shown
                this.isLoading = false;
            });
    }
});
