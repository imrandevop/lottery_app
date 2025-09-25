// User Counter with Flipping Animation

class FlippingCounter {
    constructor(containerId, apiUrl) {
        this.container = document.getElementById(containerId);
        this.apiUrl = apiUrl;
        this.currentCount = 0;
        this.targetCount = 0;
        this.digits = [];
        this.updateInterval = null;
        this.init();
    }

    init() {
        if (!this.container) {
            console.error('Counter container not found');
            return;
        }
        
        this.createCounterHTML();
        this.fetchUserCount();
        
        // Start 30-second API polling
        setInterval(() => {
            this.fetchUserCount();
        }, 30000);
    }

    createCounterHTML() {
        this.container.innerHTML = `
            <div class="user-counter-container">
                <div class="counter-display" id="counter-display">
                    <div class="counter-loading">
                        Loading<span class="loading-dots"></span>
                    </div>
                </div>
                <button class="fullscreen-btn" id="enter-fullscreen-btn" title="Fullscreen View">
                    ⛶
                </button>
            </div>
            
            <!-- Fullscreen overlay -->
            <div id="fullscreen-overlay" class="fullscreen-overlay" style="display: none;">
                <div class="fullscreen-counter">
                    <div class="fullscreen-display" id="fullscreen-counter-display">
                        <div class="counter-loading">
                            Loading<span class="loading-dots"></span>
                        </div>
                    </div>
                    <button class="fullscreen-btn exit-fullscreen-btn" id="exit-fullscreen-btn" title="Exit Fullscreen">
                        ✕
                    </button>
                </div>
            </div>
        `;
        
        // Add event listeners after HTML is created
        this.setupEventListeners();
    }

    setupEventListeners() {
        const enterBtn = document.getElementById('enter-fullscreen-btn');
        const exitBtn = document.getElementById('exit-fullscreen-btn');
        
        if (enterBtn) {
            enterBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.enterFullscreen();
            });
        }
        
        if (exitBtn) {
            exitBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.exitFullscreen();
            });
        }
    }

    async fetchUserCount() {
        try {
            const response = await fetch(this.apiUrl);
            const data = await response.json();
            
            if (response.ok && data.count !== undefined) {
                this.updateCounter(data.count);
                
                // Log for debugging
                if (data.cached) {
                    console.log(`User count loaded from cache: ${data.count}`);
                }
            } else {
                this.showError('Failed to load user count');
            }
        } catch (error) {
            console.error('Error fetching user count:', error);
            this.showError('Connection error');
        }
    }


    updateCounter(newCount) {
        this.targetCount = parseInt(newCount);
        
        // If this is the first load, show immediately
        if (this.currentCount === 0) {
            this.currentCount = this.targetCount;
            this.renderDigits();
            return;
        }
        
        // Animate the counter change
        this.animateToTarget();
    }

    animateToTarget() {
        const difference = this.targetCount - this.currentCount;
        const steps = Math.min(Math.abs(difference), 50); // Limit animation steps
        const increment = difference / steps;
        let currentStep = 0;
        
        const animate = () => {
            if (currentStep < steps) {
                this.currentCount += increment;
                this.renderDigits();
                currentStep++;
                setTimeout(animate, 50); // 50ms between steps
            } else {
                this.currentCount = this.targetCount;
                this.renderDigits();
                this.addPulseEffect();
            }
        };
        
        animate();
    }

    renderDigits() {
        const countStr = Math.floor(this.currentCount).toString().padStart(6, '0');
        const displayContainer = document.getElementById('counter-display');
        const fullscreenContainer = document.getElementById('fullscreen-counter-display');
        
        if (!displayContainer) return;
        
        // Create digit containers if they don't exist
        if (this.digits.length === 0) {
            this.createDigitContainers(6); // Always 6 digits
        }
        
        // Update each digit with flip animation
        countStr.split('').forEach((digit, index) => {
            this.updateDigit(index, digit);
        });
        
        // Update fullscreen display if it exists
        if (fullscreenContainer) {
            this.updateFullscreenDisplay(countStr);
        }
    }

    createDigitContainers(digitCount) {
        const displayContainer = document.getElementById('counter-display');
        displayContainer.innerHTML = '';
        
        this.digits = [];
        
        for (let i = 0; i < digitCount; i++) {
            const digitContainer = document.createElement('div');
            digitContainer.className = 'digit-container';
            digitContainer.innerHTML = `
                <div class="digit current" data-digit="0">0</div>
                <div class="digit" data-digit="1">1</div>
                <div class="digit" data-digit="2">2</div>
                <div class="digit" data-digit="3">3</div>
                <div class="digit" data-digit="4">4</div>
                <div class="digit" data-digit="5">5</div>
                <div class="digit" data-digit="6">6</div>
                <div class="digit" data-digit="7">7</div>
                <div class="digit" data-digit="8">8</div>
                <div class="digit" data-digit="9">9</div>
            `;
            
            displayContainer.appendChild(digitContainer);
            this.digits.push(digitContainer);
            
            // Add separator after thousands
            if (digitCount > 3 && i === digitCount - 4) {
                const separator = document.createElement('span');
                separator.className = 'digit-separator';
                displayContainer.appendChild(separator);
            }
        }
    }

    updateDigit(index, targetDigit) {
        if (!this.digits[index]) return;
        
        const digitContainer = this.digits[index];
        const currentDigitEl = digitContainer.querySelector('.digit.current');
        const targetDigitEl = digitContainer.querySelector(`[data-digit="${targetDigit}"]`);
        
        if (!currentDigitEl || !targetDigitEl) return;
        
        const currentDigit = currentDigitEl.getAttribute('data-digit');
        
        // Only animate if the digit actually changed
        if (currentDigit !== targetDigit) {
            // Remove current class
            currentDigitEl.classList.remove('current');
            
            // Add flip animation
            const isIncreasing = parseInt(targetDigit) > parseInt(currentDigit);
            currentDigitEl.classList.add(isIncreasing ? 'flip-up' : 'flip-down');
            
            // Set new current digit after a delay
            setTimeout(() => {
                // Reset all digits
                digitContainer.querySelectorAll('.digit').forEach(d => {
                    d.classList.remove('current', 'flip-up', 'flip-down');
                });
                
                // Set new current
                targetDigitEl.classList.add('current');
            }, 300);
        }
    }

    addSeparators(countStr) {
        // This is handled in createDigitContainers for static separators
        // You could enhance this for dynamic separator addition
    }

    addPulseEffect() {
        const container = this.container.querySelector('.user-counter-container');
        if (container) {
            container.classList.add('counter-pulse');
            setTimeout(() => {
                container.classList.remove('counter-pulse');
            }, 800);
        }
    }

    showError(message) {
        const displayContainer = document.getElementById('counter-display');
        if (displayContainer) {
            displayContainer.innerHTML = `
                <div class="counter-error">
                    ⚠️ ${message}
                </div>
            `;
        }
    }

    enterFullscreen() {
        const overlay = document.getElementById('fullscreen-overlay');
        if (!overlay) return;
        
        overlay.style.display = 'flex';
        this.updateFullscreenDisplay(Math.floor(this.currentCount).toString().padStart(6, '0'));
        document.body.style.overflow = 'hidden';
        
        // Add escape key listener
        this.addEscapeListener();
        
        // Prevent overlay click from closing
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }

    exitFullscreen() {
        const overlay = document.getElementById('fullscreen-overlay');
        if (!overlay) return;
        
        overlay.style.display = 'none';
        document.body.style.overflow = '';
        
        // Remove escape key listener
        this.removeEscapeListener();
    }

    addEscapeListener() {
        this.escapeHandler = (e) => {
            if (e.key === 'Escape') {
                this.exitFullscreen();
            }
        };
        document.addEventListener('keydown', this.escapeHandler);
    }

    removeEscapeListener() {
        if (this.escapeHandler) {
            document.removeEventListener('keydown', this.escapeHandler);
            this.escapeHandler = null;
        }
    }

    updateFullscreenDisplay(countStr) {
        const fullscreenContainer = document.getElementById('fullscreen-counter-display');
        if (!fullscreenContainer) return;
        
        const digits = countStr.split('').map(digit => 
            `<div class="fullscreen-digit">${digit}</div>`
        ).join('');
        
        fullscreenContainer.innerHTML = `
            <div class="fullscreen-digits-container">
                ${digits}
            </div>
        `;
    }
}

// Export for manual initialization
window.FlippingCounter = FlippingCounter;