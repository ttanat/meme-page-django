document.querySelector(".nav-item[data-target='#uploadModal']").remove()

const ProfileSettingsComponent = {
    props: {
        imageUrl: {
            type: String,
            required: false,
            default: ""
        },
        filterNsfw: {
            type: Boolean,
            required: true
        },
        userEmail: {
            type: String,
            required: false,
            default: ""
        }
    },
    data() {
        return {
            url: this.imageUrl,

            initialFilter: this.filterNsfw,
            filter: this.filterNsfw,
            savingFilter: false,

            initialEmail: this.userEmail,
            email: this.userEmail,
            savingEmail: false,

            old_password: "",
            opInvalid: false,
            password1: "",
            p1Invalid: false,
            password2: "",
            p2Invalid: false,
            changingPassword: false,

            confirmPassword: "",
            deletingAccount: false,

            inputHasImage: false,
            showDeleteBtn: true,
            savingImage: false
        }
    },
    computed: {
        passwordFormValid() {
            return this.old_password && this.password1 && this.password2 && !this.opInvalid && !this.p1Invalid && !this.p2Invalid && this.password1 === this.password2;
        },
        passwordMatch() {
            return this.password1 === this.password2;
        }
    },
    mounted() {
        if (!this.initialEmail) this.$refs.rmEmailBtn.disabled = true; 
    },
    template: (
        `<div class="w-50">
            <div class="form-group mb-5">
                <img ref="oldImage" v-show="url && !inputHasImage" :src="url" class="rounded-circle mb-3" height="100" width="100">
                <img ref="newImage" v-show="inputHasImage" class="rounded-circle mb-3" height="100" width="100">
                <br>
                <label>Profile picture</label>
                <input ref="imgInput" @change="imgInputChange" class="d-block form-control form-control-sm mb-3" type="file" name="image" accept="image/jpeg, image/png">
                <button ref="saveBtn" @click="saveImage" :class="{'not-allowed': !inputHasImage}" class="btn btn-sm btn-primary mr-3" type="button" disabled><i v-if="savingImage" class="fas fa-circle-notch fa-spin"></i><template v-else>Save</template></button>
                <button v-show="inputHasImage" @click="removeInputImage" class="btn btn-sm btn-secondary mr-3" type="button">Cancel</button>
                <button v-show="url && showDeleteBtn" @click="removeImage" class="btn btn-sm btn-danger" type="button">Remove image</button>
            </div>
            <div class="form-group mb-5">
                <div class="custom-control custom-switch mb-3">
                    <input v-model="filter" type="checkbox" class="custom-control-input" id="nsfw">
                    <label class="custom-control-label" for="nsfw">Filter NSFW content</label>
                </div>
                <button @click="changeNsfwFilter" class="btn btn-primary btn-sm"><i v-if="savingFilter" class="fas fa-circle-notch fa-spin"></i><template v-else>Save</template></button>
            </div>
            <div class="form-group mb-5">
                <label for="email">Email address</label>
                <input v-model.trim="email" @keyup="checkNewEmail" type="email" class="form-control form-control-sm mb-3" id="email" aria-describedby="emailHelp" placeholder="Email address">
                <button ref="changeEmailBtn" @click="changeEmail" :class="{'not-allowed': !email || email === initialEmail}" class="btn btn-primary btn-sm mr-2" disabled>Change email</button>
                <button ref="rmEmailBtn" @click="deleteEmail" class="btn btn-danger btn-sm">Remove email</button>
            </div>
            <div class="form-group mb-5">
                <label for="password">Password</label>
                <input v-model="old_password" @keyup="opval" :class="{'is-invalid': opInvalid}" type="password" class="form-control form-control-sm mb-3" id="password" placeholder="Old password">
                <input v-model="password1" @keyup="p1val" :class="{'is-invalid': p1Invalid}" type="password" class="form-control form-control-sm mb-3" id="password1" placeholder="New password">
                <input v-model="password2" @keyup="p2val" :class="{'is-invalid': p2Invalid, 'mb-3': passwordMatch}" type="password" class="form-control form-control-sm" id="password2" placeholder="Confirm password">
                <div v-show="!passwordMatch" class="mb-3"><small class="text-muted mb-3">Password does not match</small></div>
                <button ref="changePasswordBtn" @click="changePassword" :class="{'not-allowed': !passwordFormValid}" class="btn btn-primary btn-sm" disabled><i v-if="changingPassword" class="fas fa-circle-notch fa-spin"></i><template v-else>Change password</template></button>
            </div>
            <div class="form-group mb-5">
                <label for="delPassword">Delete account</label>
                <input v-model="confirmPassword" @keyup="confirmPasswordKeyup" type="password" class="form-control form-control-sm mb-3" id="delPassword" placeholder="Confirm password">
                <button ref="delAccountBtn" @click="deleteAccount" :class="{'not-allowed': !confirmPassword.length}" class="btn btn-danger btn-sm" disabled>Delete account</button>
            </div>
        </div>`
    ),
    methods: {
        getHeader() {
            return {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}}
        },
        imgInputChange() {
            const input = this.$refs.imgInput;
            this.inputHasImage = input.files.length === 1 && ["image/jpeg", "image/png"].includes(input.files[0].type);
            this.showDeleteBtn = this.$refs.saveBtn.disabled = !this.inputHasImage;
            if (this.inputHasImage) {
                const newImg = this.$refs.newImage;
                newImg.onload = () => {
                    URL.revokeObjectURL(newImg.src);
                }
                newImg.src = URL.createObjectURL(input.files[0]);
            }
        },
        saveImage() {
            if (confirm("Are you sure you want to change your profile picture?")) {
                this.savingImage = true;
                const data = new FormData();
                data.set("img", this.$refs.imgInput.files[0])
                axios.post(`${window.location.href}?f=image`, data, this.getHeader())
                    .then(() => this.savingImage = false)
                    .then(() => {
                        this.$refs.oldImage.onload = () => {
                            URL.revokeObjectURL(this.url)
                        }
                        const input = this.$refs.imgInput;
                        this.url = URL.createObjectURL(input.files[0]);
                        input.value = null;
                        this.imgInputChange();
                        alert("Profile picture has been changed")
                    })
                    .catch(err => console.log(err))
                    .finally(() => this.savingImage = false);
            }
        },
        removeInputImage() {
            this.$refs.imgInput.value = null;
            this.imgInputChange();
        },
        removeImage() {
            if (confirm("Are you sure you want to remove your profile picture?")) {
                axios.delete(`${window.location.href}?f=image`, this.getHeader())
                    .then(res => {if (res.status === 204) this.url = ""})
                    .catch(err => console.log(err));
            }
        },
        changeNsfwFilter() {
            if (this.filter !== this.initialFilter) {
                this.savingFilter = true;
                const data = new FormData();
                data.set("filter", this.filter);

                axios.post(`${window.location.href}?f=nsfw`, data, this.getHeader())
                    .then(() => this.savingFilter = false)
                    .then(() => alert("Preference has been saved"))
                    .catch(err => console.log(err))
                    .finally(() => this.savingFilter = false);
            } else {
                alert("Preference has been saved")
            }
        },
        checkNewEmail() {this.$refs.changeEmailBtn.disabled = !this.email || this.email === this.initialEmail},
        changeEmail() {
            if (this.email !== this.initialEmail) {
                if (this.email.match(/^\S+@\S+\.[a-zA-Z]+$/)) {
                    this.savingEmail = true;
                    const data = new FormData();
                    data.set("email", this.email);

                    axios.post(`${window.location.href}?f=email`, data, this.getHeader())
                        .then(() => this.$refs.rmEmailBtn.disabled = false)
                        .catch(err => err.response.data ? alert(err.response.data) : console.log(err))
                        .finally(() => this.savingEmail = false);
                } else {
                    alert("Please enter a valid email address")
                }
            }
        },
        deleteEmail() {
            if (confirm("Are you sure you want to remove your email from this account?")) {
                axios.delete(`${window.location.href}?f=email`, this.getHeader())
                    .then(r => {
                        if (r.status === 204) {
                            this.email = "";
                            alert("Email has been removed");
                        }
                    })
                    .catch(err => console.log(err));
            }
        },
        togglePasswordBtn() {this.$refs.changePasswordBtn.disabled = !this.passwordFormValid},
        opval() {this.opInvalid = false;this.togglePasswordBtn()},
        p1val() {this.p1Invalid = false;this.togglePasswordBtn()},
        p2val() {this.p2Invalid = false;this.togglePasswordBtn()},
        changePassword() {
            if (!this.old_password) {//.length < 6) {
                this.opInvalid = true;
                alert("Password incorrect");
                // alert("Password must be at least 6 characters");
            } else if (this.password1 !== this.password2) {
                this.p2Invalid = true;
                alert("Password does not match");
            } else if (!this.password1) {//.length < 6) {
                this.p1Invalid = true;
                alert("Password cannot be blank")
                // alert("Password must be at least 6 characters")
            } else {
                this.changingPassword = true;
                const data = new FormData();
                data.set("old_password", this.old_password);
                data.set("password1", this.password1);
                data.set("password2", this.password2);

                axios.post(`${window.location.href}?f=password`, data , this.getHeader())
                    .then(() => {
                        alert("Password has been changed. Please log back in.");
                        window.location = "/";
                    })
                    .catch(err => err.response.data ? alert(err.response.data) : console.log(err))
                    .finally(() => this.changingPassword = false);
            }
        },
        confirmPasswordKeyup() {this.$refs.delAccountBtn.disabled = !this.confirmPassword.length},
        deleteAccount() {
            if (!this.confirmPassword) {//.length < 6) {
                alert("Password incorrect");
            } else {
                if (confirm("Are you sure you want to delete your account? We're sorry to see you go :(")) {
                    axios.delete(`${window.location.href}?f=account`, this.getHeader())
                        .then(() => {
                            alert("Your account has now been deleted. Goodbye :(");
                            window.location = "/";
                        })
                        .catch(err => err.response.data ? alert(err.response.data) : console.log(err));
                }
            }
        }
    }
}

const ProfileSettingsInstance = window.location.pathname === "/settings" ? new Vue({
    el: "#psettings",
    components: {"profile-settings": ProfileSettingsComponent}
}) : undefined;

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
