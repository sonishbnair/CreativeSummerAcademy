// Activity Timer Management

class ActivityTimer {
    constructor(duration, onComplete, onTick) {
        this.duration = duration * 60; // Convert to seconds
        this.remaining = this.duration;
        this.onComplete = onComplete;
        this.onTick = onTick;
        this.isRunning = false;
        this.interval = null;
    }
    
    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.interval = setInterval(() => {
            this.remaining--;
            
            if (this.onTick) {
                this.onTick(this.remaining);
            }
            
            if (this.remaining <= 0) {
                this.stop();
                if (this.onComplete) {
                    this.onComplete();
                }
            }
        }, 1000);
    }
    
    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        this.isRunning = false;
    }
    
    pause() {
        this.stop();
    }
    
    resume() {
        this.start();
    }
    
    getTimeString() {
        const minutes = Math.floor(this.remaining / 60);
        const seconds = this.remaining % 60;
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    getProgress() {
        return ((this.duration - this.remaining) / this.duration) * 100;
    }
}

// Session Recovery
class SessionRecovery {
    constructor() {
        this.storageKey = 'galactic_activity_session';
    }
    
    saveSession(sessionData) {
        localStorage.setItem(this.storageKey, JSON.stringify(sessionData));
    }
    
    getSession() {
        const data = localStorage.getItem(this.storageKey);
        return data ? JSON.parse(data) : null;
    }
    
    clearSession() {
        localStorage.removeItem(this.storageKey);
    }
    
    hasActiveSession() {
        return this.getSession() !== null;
    }
}

// Activity Setup Form Management
class ActivitySetup {
    constructor() {
        this.selectedMaterials = [];
        this.selectedObjectives = [];
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Material selection
        document.querySelectorAll('input[name="materials"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.selectedMaterials.push(e.target.value);
                } else {
                    this.selectedMaterials = this.selectedMaterials.filter(m => m !== e.target.value);
                }
                this.updateMaterialCount();
            });
        });
        
        // Objective selection
        document.querySelectorAll('input[name="objectives"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.selectedObjectives.push(e.target.value);
                } else {
                    this.selectedObjectives = this.selectedObjectives.filter(o => o !== e.target.value);
                }
            });
        });
        
        // Form submission
        const form = document.getElementById('activity-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitForm();
            });
        }
    }
    
    updateMaterialCount() {
        const countElement = document.getElementById('material-count');
        const minMaterials = parseInt(document.getElementById('min-materials').textContent);
        const maxMaterials = parseInt(document.getElementById('max-materials').textContent);
        
        if (countElement) {
            countElement.textContent = this.selectedMaterials.length;
            
            if (this.selectedMaterials.length < minMaterials) {
                countElement.style.color = 'red';
            } else if (this.selectedMaterials.length > maxMaterials) {
                countElement.style.color = 'red';
            } else {
                countElement.style.color = 'green';
            }
        }
    }
    
    submitForm() {
        const duration = document.getElementById('duration').value;
        const category = document.getElementById('category').value;
        
        if (!duration || !category) {
            // alert('Please select duration and category'); // Removed alert
            return;
        }
        
        if (this.selectedMaterials.length < 3 || this.selectedMaterials.length > 8) {
            // alert('Please select between 3 and 8 materials'); // Removed alert
            return;
        }
        
        if (this.selectedObjectives.length === 0) {
            // alert('Please select at least one learning objective'); // Removed alert
            return;
        }
        
        // Create form data and submit
        const formData = new FormData();
        formData.append('duration', duration);
        formData.append('category', category);
        
        this.selectedMaterials.forEach(material => {
            formData.append('materials', material);
        });
        
        this.selectedObjectives.forEach(objective => {
            formData.append('objectives', objective);
        });
        
        fetch('/activities/generate', {
            method: 'POST',
            body: formData
        }).then(response => {
            if (response.redirected) {
                window.location.href = response.url;
            }
        }).catch(error => {
            console.error('Error:', error);
            // alert('Error generating activity. Please try again.'); // Removed alert
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize activity setup if on setup page
    if (document.getElementById('activity-form')) {
        new ActivitySetup();
    }
    

    
    // Session recovery
    const sessionRecovery = new SessionRecovery();
    if (sessionRecovery.hasActiveSession()) {
        const session = sessionRecovery.getSession();
        if (session && session.status === 'active') {
            // Show recovery option
            const recoveryDiv = document.createElement('div');
            recoveryDiv.className = 'alert alert-warning';
            recoveryDiv.innerHTML = `
                <strong>Activity in Progress!</strong> 
                You have an active activity. 
                <a href="/activities/${session.session_id}/active" class="btn btn-primary">Continue Activity</a>
                <button onclick="clearSession()" class="btn btn-secondary">Start New</button>
            `;
            document.querySelector('.container').prepend(recoveryDiv);
        }
    }
});

function clearSession() {
    const sessionRecovery = new SessionRecovery();
    sessionRecovery.clearSession();
    location.reload();
} 