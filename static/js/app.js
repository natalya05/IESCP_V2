
Vue.component('admin-dashboard', {
    template: '#admin-dashboard',
    delimiters: ['[[', ']]'],
    data() {
        return {
            users: [], 
            campaigns: [], 
            adRequests: [], 
            sponsors: [],
            error: null, 
            successMessage: null 
        };
    },
    created() {
        this.fetchAdminData();
    },
    methods: {
        fetchAdminData() {
            axios.get('/admin/dashboard')
                .then(response => {
                    this.users = response.data.users || [];
                    this.campaigns = response.data.campaigns || [];
                    this.adRequests = response.data.ad_requests || [];
                    this.sponsors = response.data.sponsors || [];
                })
                .catch(error => {
                    console.error('Error fetching admin data:', error);
                    this.error = 'Failed to load admin dashboard data.';
                });
        },
        approveSponsor(userId) {
            axios.patch(`/approve_sponsor/${userId}`)
                .then(() => {
                    alert("Sponsor approved successfully!");
                })
                .catch(error => {
                    console.error("Error approving sponsor:", error);
                });
        },
        deleteCampaign(campaignId) {
            if (confirm('Are you sure you want to delete this campaign and all its related ad requests?')) {
                axios.delete(`/delete_campaignadmin/${campaignId}`)
                    .then(response => {
                        this.successMessage = response.data.message || 'Campaign deleted successfully!';
                        this.campaigns = this.campaigns.filter(campaign => campaign.id !== campaignId);
                    })
                    .catch(error => {
                        console.error('Error deleting campaign:', error);
                        this.error = error.response?.data?.message || 'Failed to delete campaign.';
                    });
            }
        },
        deleteAdRequest(adRequestId) {
            if (confirm('Are you sure you want to delete this ad request?')) {
                axios.delete(`/delete_adrequest/${adRequestId}`)
                    .then(response => {
                        this.successMessage = response.data.message || 'Ad request deleted successfully!';
                        this.adRequests = this.adRequests.filter(adRequest => adRequest.id !== adRequestId);
                    })
                    .catch(error => {
                        console.error('Error deleting ad request:', error);
                        this.error = error.response?.data?.message || 'Failed to delete ad request.';
                    });
            }
        },
        deleteUser(userId) {
            if (confirm('Are you sure you want to delete this user and all associated data?')) {
                axios.delete(`/delete_user/${userId}`)
                    .then(response => {
                        this.successMessage = response.data.message || 'User deleted successfully.';
                        this.users = this.users.filter(user => user.id !== userId);
                    })
                    .catch(error => {
                        console.error('Error deleting user:', error);
                        this.error = error.response?.data?.message || 'Failed to delete user.';
                    });
            }
        },
        logout() {
            this.$root.logout(); 
        }
    }
});


// Sponsor Dashboard 
Vue.component('sponsor-dashboard', {
    template: '#sponsor-dashboard',
    delimiters: ['[[', ']]'],
    data() {
        return {
            user: '', 
            searchQuery: '', 
            searchResults: [], 
            searchError: '',
            campaigns: [], 
            influencers: [],
            newCampaign: { 
                name: '',
                description: '',
                start_date: '',
                end_date: '',
                budget: '',
                visibility: 'public',
                goals: ''
            },
            newAdRequest: { 
                campaign_id: '',
                influencer_id: '',
                requirements: '',
                payment_amount: ''
            },
            adRequests: [], 
            editingCampaignId: null,
            editingAdRequestId: null,
            flashMessage: '' 
        };
    },
    created() {
        
        axios.get('/sponsor_dashboard')
            .then(response => {
                this.user = response.data.user;
                this.campaigns = response.data.campaigns || [];
                this.influencers = response.data.influencers || [];
                this.adRequests = response.data.ad_requests || []; 
            })
            .catch(error => {
                console.error('Error fetching sponsor data:', error);
            });
    },
    methods: {
        searchInfluencers() {
            if (!this.searchQuery.trim()) {
                this.searchError = 'Please enter a search term.';
                return;
            }
            this.searchError = ''; 
            axios.get('/sponsor_dashboard', { params: { search_query: this.searchQuery } })
                .then(response => {
                    this.searchResults = response.data.search_results || [];
                })
                .catch(error => {
                    console.error('Error searching influencers:', error);
                    this.searchError = 'Failed to search for influencers. Please try again.';
                });
        },
        createCampaign() {
            axios.post('/sponsor_dashboard', this.newCampaign)
                .then(response => {
                    this.flashMessage = response.data.message || 'Campaign created successfully!';
                    this.campaigns.push({ ...this.newCampaign, id: response.data.id });
                    this.newCampaign = {
                        name: '',
                        description: '',
                        start_date: '',
                        end_date: '',
                        budget: '',
                        visibility: 'public',
                        goals: ''
                    };
                })
                .catch(error => {
                    console.error('Error creating campaign:', error);
                    this.flashMessage = 'Failed to create campaign. Please try again.';
                });
        },
        createAdRequest() {
            axios.post('/create_adreq', this.newAdRequest)
                .then(response => {
                    this.flashMessage = response.data.message || 'Ad request created successfully!';
                    this.adRequests.push(response.data.ad_request);
                    this.newAdRequest = {
                        campaign_id: '',
                        influencer_id: '',
                        requirements: '',
                        payment_amount: ''
                    };
                })
                .catch(error => {
                    console.error('Error creating ad request:', error);
                    this.flashMessage = 'Failed to create ad request. Please try again.';
                });
        },
        editCampaign(campaign) {
           
            this.newCampaign = { ...campaign }; 
            this.editingCampaignId = campaign.id; 
        },
        saveCampaign() {
            axios.post(`/update_campaign/${this.editingCampaignId}`, this.newCampaign)
                .then(response => {
                    this.flashMessage = response.data.message || 'Campaign updated successfully!';
                    const index = this.campaigns.findIndex(c => c.id === this.editingCampaignId);
                    if (index !== -1) {
                        this.campaigns[index] = { ...this.newCampaign, id: this.editingCampaignId };
                    }
        
                    this.newCampaign = {
                        name: '',
                        description: '',
                        start_date: '',
                        end_date: '',
                        budget: '',
                        visibility: 'public',
                        goals: ''
                    };
                    this.editingCampaignId = null;
                })
                .catch(error => {
                    console.error('Error updating campaign:', error);
                    this.flashMessage = 'Failed to update campaign. Please try again.';
                });
        },
        updateCampaign(campaignId, updatedData) {
            axios.post(`/update_campaign/${campaignId}`, updatedData)
                .then(response => {
                    const updatedCampaign = response.data.campaign;
                    const index = this.campaigns.findIndex(campaign => campaign.id === campaignId);
                    if (index !== -1) {
                        this.campaigns.splice(index, 1, updatedCampaign);
                    }
                    this.flashMessage = response.data.message || 'Campaign updated successfully!';
                })
                .catch(error => {
                    console.error('Error updating campaign:', error);
                    this.flashMessage = 'Failed to update campaign. Please try again.';
                });
        },
        
        deleteCampaign(id) {
            if (!confirm('Are you sure you want to delete this campaign?')) return;
    
            axios.post(`/delete_campaign/${id}`)
                .then(response => {
                    this.flashMessage = response.data.message || 'Campaign deleted successfully!';
                    this.campaigns = this.campaigns.filter(campaign => campaign.id !== id);
                })
                .catch(error => {
                    console.error('Error deleting campaign:', error);
                    this.flashMessage = 'Failed to delete campaign. Please try again.';
                });
        },
        editAdRequest(adRequest) {
            this.newAdRequest = { ...adRequest };
            this.editingAdRequestId = adRequest.id; 
        },
        saveAdRequest() {
            axios.post(`/update_ad_request/${this.editingAdRequestId}`, this.newAdRequest)
                .then(response => {
                    this.flashMessage = response.data.message || 'Ad request updated successfully!';
                    const index = this.adRequests.findIndex(ad => ad.id === this.editingAdRequestId);
                    if (index !== -1) {
                        this.adRequests[index] = { ...this.newAdRequest, id: this.editingAdRequestId };
                    }
                    this.newAdRequest = {
                        campaign_id: '',
                        influencer_id: '',
                        requirements: '',
                        payment_amount: ''
                    };
                    this.editingAdRequestId = null;
                })
                .catch(error => {
                    console.error('Error updating ad request:', error);
                    this.flashMessage = 'Failed to update ad request. Please try again.';
                });
        },
        updateAdRequest(adRequestId, updatedData) {
            axios.post(`/update_ad_request/${adRequestId}`, updatedData)
                .then(response => {
                    const updatedAdRequest = response.data.ad_request;
                    const index = this.adRequests.findIndex(req => req.id === adRequestId);
                    if (index !== -1) {
                        this.adRequests.splice(index, 1, updatedAdRequest);
                    } else {
                        console.warn(`Ad request with ID ${adRequestId} not found in the list.`);
                    }
                    this.flashMessage = response.data.message || 'Ad request updated successfully!';
                })
                .catch(error => {
                    console.error('Error updating ad request:', error);
                    this.flashMessage = 'Failed to update ad request. Please try again.';
                });
        },
        
        deleteAdRequest(id) {
            if (!confirm('Are you sure you want to delete this ad request?')) return;
    
            axios.post(`/delete_ad_request/${id}`)
                .then(response => {
                    this.flashMessage = response.data.message || 'Ad request deleted successfully!';
                    this.adRequests = this.adRequests.filter(adRequest => adRequest.id !== id);
                })
                .catch(error => {
                    console.error('Error deleting ad request:', error);
                    this.flashMessage = 'Failed to delete ad request. Please try again.';
                });
        },
        trigger_celery_job: function () {
            fetch("/trigger-celery-job").then(r=> r.json()
            ).then(d=>{
                console.log("celery task details:",d);
                window.location.href= "/download-file"
              
            })
        },
        logout() {
            this.$root.logout(); 
        }
    }
});


// Influencer Dashboard Component
Vue.component('influencer-dashboard', {
    template: '#influencer-dashboard',
    delimiters: ['[[', ']]'],
    data() {
        return {
            user: '', 
            publicCampaigns: [], 
            adRequests: [], 
            searchQuery: {
                name: '', 
                budget: '' 
            },
            searchResults: [],
        };
    },
    created() {
        this.fetchInfluencerData();
    },
    methods: {
        
        fetchInfluencerData() {
            axios.get('/influencer/dashboard')
                .then(response => {
                    console.log("API Response:", response.data);
                    this.user = response.data.user || 'Influencer';
                    this.publicCampaigns = response.data.public_campaigns || [];
                    // this.adRequests = response.data.ad_requests || [];
                    this.adRequests = response.data.ad_requests.map(req => ({
                        ...req,
                        negotiated_amount: req.payment_amount 
                    }));
                })
                .catch(error => {
                    console.error('Error fetching influencer data:', error);
                    alert('Failed to fetch influencer data. Please try again.');
                });
        },
        negotiateAmount(adRequestId, negotiatedAmount) {
            if (!negotiatedAmount || isNaN(negotiatedAmount)) {
                alert('Please enter a valid amount to negotiate.');
                return;
            }
            axios.post('/negotiate', {
                ad_request_id: adRequestId,
                req_amount: negotiatedAmount
            })
                .then(response => {
                    alert(response.data.message || 'Negotiation request sent successfully.');
                })
                .catch(error => {
                    console.error('Error negotiating amount:', error);
                    alert('Failed to send negotiation request. Please try again.');
                });
        },
       
        searchPublicCampaigns() {
            axios.get('/search_campaigns', {
                params: {
                    name: this.searchQuery.name,
                    budget: this.searchQuery.budget || undefined 
                }
            })
                .then(response => {
                    this.searchResults = response.data.campaigns || [];
                })
                .catch(error => console.error('Error searching campaigns:', error));
        },
        updateAdRequestStatus(adRequestId, status) {
            axios.post('/update_ad_request_status', {
                ad_request_id: adRequestId,
                status: status
            })
                .then(response => {
                    
                    const adRequest = this.adRequests.find(req => req.id === adRequestId);
                    if (adRequest) {
                        adRequest.status = status; // Update status dynamically
                    }
                })
                .catch(error => {
                    console.error('Error updating ad request status:', error);
                    alert('Failed to update status. Please try again.');
                });
        },

        
        logout() {
            this.$root.logout(); 
        }
    }
});


new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data: {
        isLoginVisible: true,
        isHomeVisible : true,
        isRegisterVisible: false,
        loginUsername: '',
        loginPassword: '',
        registerUsername: '',
        registerPassword: '',
        loginError: '',
        registerError: '',
        registerSuccess: '',
        role: '',
        isLoading: false, 
        message:'Welcome to Influencer Engagement and Sponsorship Coordination Platform'
    },
    methods: {
        showLoginForm() {
            this.isLoginVisible = true;
            this.isRegisterVisible = false;
            this.isHomeVisible = false;
            this.clearMessages();
        },
        showRegisterForm() {
            this.isRegisterVisible = true;
            this.isLoginVisible = false;
            this.isHomeVisible = false;
            this.clearMessages();
        },
        clearMessages() {
            this.loginError = '';
            this.registerError = '';
            this.registerSuccess = '';
        },
        
        handleLogin() {
            this.isLoading = true;
            axios.post('/api/login', {
                name: this.loginUsername,
                password: this.loginPassword
            })
                .then(response => {
                    if (response.data.success) {
                        this.role = response.data.role[0];
                        this.isLoginVisible = false;
                    } else {
                        this.loginError = response.data.error || 'Login failed.';
                    }
                })
                .catch(error => {
                    console.error('Login failed:', error);
                    this.loginError = error.response?.data?.error || 'An error occurred during login.';
                })
                .finally(() => {
                    this.isLoading = false;
                });
        },
        handleRegister() {
            this.isLoading = true;
            axios.post('/register', {
                name: this.registerUsername,
                password: this.registerPassword,
                role: this.selectedRole,
                email: this.registerEmail,
            })
                .then(response => {
                    if (response.data.success) {
                        this.registerSuccess = response.data.message || 'Registration successful!';
                        this.registerError = ''; 
                        this.showLoginForm(); 
                    } else {
                        this.registerError = response.data.error || 'Registration failed.';
                        this.registerSuccess = ''; 
                    }
                })
                .catch(error => {
                    console.error('Registration failed:', error);
                    this.registerError = error.response?.data?.error || 'An error occurred during registration.';
                    this.registerSuccess = ''; 
                })
                .finally(() => {
                    this.isLoading = false;
                });
        },
        
        logout() {
            this.isLoading = true;
            axios.post('/api/logout')
                .then(response => {
                    if (response.data.success) {
                        window.location.href = '/'; 
                    } else {
                        console.error('Logout failed:', response.data.message);
                    }
                })
                .catch(error => {
                    console.error('Logout request failed:', error);
                })
                .finally(() => {
                    this.isLoading = false;
                });
        }
    },
    created() {
        axios.get('/api/user-role')
            .then(response => {
                this.role = response.data.role || '';
                if (this.role) {
                    this.isLoginVisible = false;
                }
            })
            .catch(error => console.error('Error fetching user role:', error));
    }
});
