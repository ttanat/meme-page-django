function night(){}

document.querySelector(".nav-item[data-target='#uploadModal']").remove()

// Ensure same information not submitted
document.querySelector("#editPage").onsubmit = (e) => {
    e.preventDefault();
    if (!(document.querySelector("[name=displayName]").value.trim() === dname && document.querySelector("[name=description]").value.trim() === description
                    && document.querySelector(`#privacy${privacy}`).checked && document.querySelector(`#perm${perms}`).checked)) {
        e.target.submit();
    }
}

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

const ProfileImageComponent = {
    props: {
        pageName: {
            type: String,
            required: true
        },
        pageUrl: {
            type: String,
            required: false,
            default: ""
        }
    },
    data() {
        return {
            pname: this.pageName,
            purl: this.pageUrl,
            inputHasImage: false,
            showDeleteBtn: true
        }
    },
    computed: {
        getToken() {return getCookie('csrftoken')}
    },
    template: (
        `<div>
            <img v-show="purl && !inputHasImage" class="rounded-circle mb-3" :src="purl" height="100" width="100">
            <img ref="newImage" v-show="inputHasImage" class="rounded-circle mb-3" height="100" width="100">
            <form :action="'/page/'+pname+'/settings'" method="POST" enctype="multipart/form-data">
                <input type="hidden" name="csrfmiddlewaretoken" :value="getToken">
                <label>Page image</label>
                <input ref="imgInput" @change="inputChange" class="d-block form-control form-control-sm mb-3" type="file" name="image" accept="image/jpeg, image/png">
                <button ref="saveBtn" :class="{'not-allowed': !inputHasImage}" class="btn btn-sm btn-primary mr-3" type="submit" disabled>Save</button>
                <button v-show="inputHasImage" @click="removeInputImage" class="btn btn-sm btn-secondary mr-3" type="button">Cancel</button>
                <button v-show="showDeleteBtn && purl" @click="deleteImage" class="btn btn-sm btn-danger" type="button">Delete image</button>
            </form>
        </div>`
    ),
    methods: {
        inputChange() {
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
        removeInputImage() {
            this.$refs.imgInput.value = null;
            this.inputChange();
        },
        deleteImage() {
            if (confirm("Are you sure you want to delete this page's image?")) {
                axios.delete(`${window.location.href}?d=image`, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                    .then(res => {if (res.status === 204) this.purl = ""})
                    .catch(err => console.log(err));
            }
        }
    }
}

const ProfileImageInstance = new Vue({el: "#edit-image-div", components: {"edit-image-form": ProfileImageComponent}})


const cm = JSON.parse(document.querySelector("#current-mods").textContent);

const MODS_STATE = {
    usernames: [USERNAME, ...cm],
    getLength() {
        return this.usernames.length;
    },
    checkExists(username) {
        return this.usernames.includes(username);
    },
    addUser(username) {
        if (this.getLength() < 20) this.usernames.push(username);
    },
    removeUsers(users_to_remove) {
        /* Takes in list of usernames */
        this.usernames = this.usernames.filter(m => !users_to_remove.includes(m));
    }
}

const CurrentModsComponent = {
    props: {
        mod: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            isActive: false
        }
    },
    template: `<button @click="toggleActive" type="button" :class="{active: isActive}" class="list-group-item list-group-item-action">{{ mod }}</button>`,
    methods: {
        toggleActive() {this.isActive = !this.isActive}
    }
}

const CurrentModsInstance = new Vue({
    el: "#current-mod-settings",
    data: {
        mods: [...cm]
    },
    mounted() {
        this.disableBtn()
    },
    components: {
        "current-mods": CurrentModsComponent
    },
    methods: {
        removeMods() {
            const to_remove = this.$children.filter(m => m.isActive).map(m => m.mod);
            if (to_remove.length && confirm(`Are you sure you want to remove ${to_remove.length > 1 ? "these moderators" : "this moderator"}?`)) {
                axios.delete(`${window.location.href}?d=mods&${to_remove.map(m => `u=${m}`).join("&")}`, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                    .then(res => {
                        this.mods = this.mods.filter(m => !to_remove.includes(m));
                        MODS_STATE.removeUsers(to_remove);
                        this.disableBtn();
                    })
                    .catch(err => console.log(err));
            }
        },
        disableBtn() {
            this.$refs.removeModBtn.disabled = !this.mods.length;
        }
    }
})

const AddModsComponent = {
    props: {
        mod: {
            type: String,
            required: true
        }
    },
    template: `<button @click="$emit('remove-event', mod)" type="button" class="list-group-item list-group-item-action">{{ mod }}</button>`
}

const AddModsInstance = new Vue({
    el: "#add-mod-settings",
    data: {
        mods: [],
        newModUsername: ""
    },
    components: {
        "mods-to-add": AddModsComponent
    },
    methods: {
        addMod() {
            const val = this.newModUsername;
            if (!val.match(/^[a-z0-9_]+$/i) || val.length > 32) {
                alert("Please enter a valid username");
            } else if (MODS_STATE.getLength() >= 20) {
                alert("Maximum number of moderators reached");
            } else if (MODS_STATE.checkExists(val)) {
                alert("Moderator already exists");
            } else {
                this.mods.push(val);
                MODS_STATE.addUser(val);
                this.newModUsername = "";
                this.$refs.sendBtn.disabled = false;
            }
        },
        removeNewMod(mod) {
            const i = this.mods.findIndex(m => m === mod);
            this.mods.splice(i, 1);
            if (!this.mods.length) this.$refs.sendBtn.disabled = true;
            MODS_STATE.removeUsers([mod]);
        }
    }
})


