// Works with both subscribe and follow button
const FollowButtonComponent = {
    props: {
        following: {
            type: Boolean,
            required: true
        },
        isProfile: {
            type: Boolean,
            required: true
        }
    },
    data() {
        return {
            is_following: this.following,
            action: this.isProfile ? "follow" : "subscribe"
        }
    },
    computed: {
        btnText() {
            return this.isProfile ? `Follow${this.is_following ? "ing" : ""}` : `Subscribe${this.is_following ? "d" : ""}`;
        },
        btnTitle() {
            return this.is_following ? `Un${this.action}` : "";
        }
    },
    template: `<button @click="follow" :class="[is_following ? 'btn-outline-success' : 'btn-success']" class="btn btn-sm follow-btn m-1" :title="btnTitle">{{ btnText }}</button>`,
    methods: {
        follow() {
            if (checkAuth()) {
                axios.get(`/${this.action}?${this.isProfile ? `u=${USER_PAGE}` : `p=${PAGE_NAME}`}`, {headers: {"X-Requested-With": "XMLHttpRequest"}})
                    .then(res => this.isProfile ? res.data.following : res.data.subscribed)
                    .then(f => {
                        this.is_following = f;
                        f ? document.querySelector(`#${this.isProfile ? "follower" : "sub"}-count`).textContent++ : document.querySelector(`#${this.isProfile ? "follower" : "sub"}-count`).textContent--;
                    })
                    .catch(err => display_error(err))
            }
        }
    }
}

const FollowButtonInstance = PN.startsWith("/user/") || (PN.startsWith("/page/") && !IS_PAGE_ADMIN) ? new Vue({
    el: "#follow-btn",
    components: {"follow-button": FollowButtonComponent}
}) : undefined;


// Works for updating bio in profile page and updating description in meme page
const EditBioComponent = {
    props: {
        bioOrDesc: {
            type: String,
            default: "",
            required: true
        },
        addText: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            bio: this.bioOrDesc,
            bioStyle: {
                fontSize: "14px",
                whiteSpace: "pre-wrap"
            },
            newBio: this.bioOrDesc,
            textareaStyle: {
                width: "100%",
                border: "none",
                borderRadius: "3px",
                paddingLeft: "3px",
                fontSize: "14px"
            },
            editing: false,
            updating: false
        }
    },
    template: (
        `<div>
            <div v-show="!editing" :style="bioStyle">
                <span v-if="updating">Updating <i class="fas fa-circle-notch fa-spin"></i></span><span v-else>{{ bio }}</span>&ensp;<small v-show="!updating" @click="editBio" class="text-muted pointer"><span v-if="!bio" style="font-size: 13px;">Add {{ addText }}&ensp;</span><i class="fas fa-pen"></i></small>
            </div>
            <textarea ref="textarea" v-show="editing" v-model.trim="newBio" :style="textareaStyle" placeholder="Add your page description here!" rows="3"></textarea>
            <span>
                <small v-show="editing" @click="editBio" class="text-muted pointer">Close</small>
                <small v-show="editing" @click="saveNew" class="text-muted pointer">&emsp;Save</small>
            </span>
        </div>`
    ),
    methods: {
        editBio() {
            this.editing = !this.editing;
            if (this.editing) this.$nextTick(() => this.$refs.textarea.focus());
        },
        saveNew() {
            const data = new FormData();
            data.set("nb", this.newBio);
            this.editing = false;

            if (data.get("nb") !== this.bio.trim()) {
                if (PN.startsWith("/page/") && IS_PAGE_ADMIN) data.set("n", PAGE_NAME);
                this.updating = true;

                axios.post(data.has("n") ? "/updateDesc" : "/updateBio", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                    .then(res => res.data)
                    .then(response => {
                        this.bio = this.newBio = response["nb"];
                    })
                    .catch(err => {
                        this.editing = true;
                        display_error(err);
                    })
                    .finally(() => this.updating = false);
            }
        }
    }
}

const EditBioInstance = PN === "/profile" || (PN.startsWith("/page/") && IS_PAGE_ADMIN) ? new Vue({
    el: "#vue-bio",
    components: {"bio-desc": EditBioComponent}
}) : undefined;
