const sidebar_links = document.querySelectorAll(".sidebar-link");
if (PN.startsWith("/user/")) {
    var sl = sidebar_links[0];
    document.querySelector("#page").textContent = USER_PAGE;
} else if (PN.startsWith("/profile")) {
    document.querySelector("#page").textContent = "Profile";
    for (let i = 0, n = sidebar_links.length; i < n; i++) {
        if (sidebar_links[i].href === "javascript:void(0);") {
            var sl = sidebar_links[i];
            document.querySelector("#profile-page").textContent = sl.dataset.profilePage;
            break;
        }
    }
}
if (sl) {
    sl.style.backgroundColor = "#333333";
    sl.style.color = "green";
}

const StatsComponent = {
    data() {
        return {
            clout: 0,
            followers: 0,
            following: 0
        }
    },
    mounted() {
        const is_profile_page = PN.startsWith("/profile");
        axios.get(`/api/pstats/?${is_profile_page ? "p=1" : `u=${USER_PAGE}`}`)
            .then(res => {
                this.clout = res.data.clout;
                this.followers = res.data.num_followers;
                this.following = res.data.num_following;
            })
            .catch(err => display_error(err));
    },
    template: (
        `<table class="mb-3 w-100 text-center">
            <tr>
                <td title="Total points">{{ clout }}</td>
                <td class="pointer" id="follower-count">{{ followers }}</td>
                <td class="pointer">{{ following }}</td>
            </tr>
            <tr>
                <td title="Total points"><small>clout</small></td>
                <td class="pointer"><small>followers</small></td>
                <td class="pointer"><small>following</small></td>
            </tr>
        </table>`
    )
}

const StatsInstance = new Vue({
    el: "#pstats",
    components: {"profile-stats": StatsComponent}
})

function update_profile_pic() {
    const file = document.querySelector("#updateProfilePic").files[0];
    if (!file) {
        alert("Please select a file.");
    } else if (!["image/jpeg", "image/png"].includes(file.type)) {
        alert("Supported media types: JPEG, PNG");
    } else if (confirm('Are you sure you want to change your profile picture?')) {
        const textBtn = document.querySelector("#editProfilePic");
        textBtn.innerHTML = `&nbsp;Updating <i class="fas fa-circle-notch fa-spin"></i>`;
        const data = new FormData();
        data.set("img", file);

        axios.post("/settings?f=image", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
            .then(() => {
                const ppc = document.querySelector("#profile-pic-container");
                if (ppc.firstChild.tagName !== "IMG") ppc.innerHTML = '<img class="rounded-circle" id="profile-pic" height="50" width="50">';
                // Add image to img element
                const new_src = URL.createObjectURL(file);
                ppc.firstChild.src = new_src;
                // Change profile picture in nav bar
                const pi = document.querySelector("#profile-image");
                if (pi.firstChild.tagName !== "IMG") pi.innerHTML = `<img class="rounded-circle" id="profile-image" height="21" width="21">`;
                pi.firstChild.src = new_src;
            })
            .catch(err => {console.log(err);display_error(err.response.data || err)})
            .finally(() => textBtn.innerHTML = `&nbsp;Edit profile picture`);
    }
}

const TileComponent = {
    props: {
        tile: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            tileStyle: {
                // margin: "1%",
                height: "0",
                position: "relative",
                width: "30%",
                paddingBottom: "30%"
            },
            playIconStyle: {
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                position: "absolute",
                zIndex: "2",
                top: "0",
                left: "0",
                bottom: "0",
                right: "0",
                fontSize: "1.62rem",
                color: "whitesmoke"
            },
            contentStyle: {
                objectFit: "cover",
                position: "absolute",
                height: "100%",
                width: "100%"
            }
        }
    },
    computed: {
        isImg() {return ["image/jpeg", "image/png"].includes(this.tile.content_type)},
        isGif() {return this.tile.content_type === "image/gif"}
    },
    template: (
        `<div class="tile" :style="tileStyle" @contextmenu.prevent>
            <a :href="'/m/'+tile.uuid" target="_blank" draggable="false">
                <i v-if="!isImg && !isGif" class="fas fa-play" :style="playIconStyle"></i>
                <h5 v-else-if="isGif" :style="playIconStyle">GIF</h5>
                <video v-if="!isImg" ref="vid" :src="tile.url" preload="metadata" loop :style="contentStyle" draggable="false"></video>
                <img v-else :src="tile.url" :style="contentStyle" draggable="false">
            </a>
        </div>`
    )
}

const TilesInstance = PN === "/profile" || PN === "/profile/likes" || PN.startsWith("/user/") ? new Vue({
    el: "#tiles",
    mounted() {
        this.loadTiles();
        createScrollObserver(this, this.loadTiles);
    },
    updated() {
        updateScrollObserver(this);
    },
    data: {
        tiles: [],
        next: PN === "/profile" ? "/api/pmemes" : PN === "/profile/likes" ? "/api/plikes" : `/api/umemes/?u=${USER_PAGE}`,
        no_content: false
    },
    methods: {
        loadTiles() {
            if (this.next) {
                axios.get(this.next)
                    .then(res => {
                        if (res.data.results.length) {
                            this.tiles.push(...res.data.results);
                            this.next = res.data.next;
                        } else {
                            this.no_content = true;
                        }
                    })
                    .catch(err => console.log(err));
            }
        }
    },
    components: {
        "tile-items": TileComponent
    }
}) : undefined;

const MyCommentComponent = {
    props: {
        comment: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            listStyle: {
                fontSize: "15px",
            },
            contentStyle: {
                height: "15rem",
                borderRadius: ".5rem"
            }
        }
    },
    computed: {
        rpattern() {
            return this.comment.content.match(/^@([a-z0-9_]+) /i);
        },
        contentAfterMention() {
            return this.comment.content.slice(this.comment.content.indexOf(" "));
        },
        replyingTo() {
            return this.comment.rt && this.rpattern ? this.rpattern[1] : this.comment.rt;
        }
    },
    template: (
        `<div class="row list-row my-4">
            <div>
                <div class="list-content" :style="listStyle"><span v-if="comment.rt && rpattern"><a :href="'/user/'+rpattern[1]" target="_blank">{{ rpattern[0] }}</a>{{ contentAfterMention }}</span><template v-else>{{ comment.content }}</template> {{ comment.rt ? " " : "" }}<small v-if="comment.rt" class="text-muted">replying to {{ replyingTo }}</small></div>
                <a v-if="comment.url" :href="'/img?c='+comment.uuid" target="_blank"><img :src="comment.url" :style="contentStyle" class="mt-1"></a><br v-if="comment.url">
                <a :href="'/m/'+comment.m_uuid" target="_blank"><small class="text-muted">Go to meme</small>&nbsp;<i class="small fas fa-external-link-alt"></i></a>
            </div>
        </div>`
    )
}

const MyCommentInstance = PN === "/profile/comments" ? new Vue({
    el: "#profile-comments",
    data: {
        comments: [],
        next: "/api/pcomments",
        scrollObserver: null,
        scrollRoot: null,
        loading: false
    },
    components: {
        "my-comments": MyCommentComponent
    },
    mounted() {
        this.loadMore();
        createScrollObserver(this, this.loadMore);
    },
    updated() {
        updateScrollObserver(this);
    },
    methods: {
        loadMore() {
            if (this.next === null) return false;
            this.loading = true;
            axios.get(this.next)
                .then(res => {
                    this.comments.push(...res.data.results);
                    this.next = res.data.next;
                })
                .catch(err => console.log(err))
                .finally(() => this.loading = false);
        }
    }
}) : undefined;

const NewPageComponent = {
    data() {
        return {
            defaultText: "Letters, numbers, and underscores only.",
            nameTakenText: "Page name already taken.",
            pageName: "",
            turnRed: false,
            smallPageNameText: "Letters, numbers, and underscores only.",
            TAKEN_PAGE_NAMES: [],
            pageDisplayName: "",
            pagePrivacy: 1,
            pagePermissions: 1
        }
    },
    template: (
        `<div class="modal fade" id="newMemePage" tabindex="-1" role="dialog" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content text-light">
                    <div class="modal-header">
                        <h5 class="modal-title">Create a Meme Page!</h5>
                    </div>
                    <div class="modal-body">
                        <label>Page Name</label>
                        <br>
                        <input v-model.trim="pageName" @keyup="pageNameValidChars" :class="{'is-invalid': turnRed}" type="text" class="input-form" maxlength="64" autocomplete="off">
                        <small ref="smallPageName" :class="{red: turnRed}">{{ smallPageNameText }}</small>
                        <br><br>
                        <label>Display Name <span class="text-muted" style="font-size: 14px;"><i class="far fa-question-circle" data-toggle="tooltip" title="Page name will be shown if display name is empty"></i></span></label>
                        <input v-model.trim="pageDisplayName" type="text" class="input-form" maxlength="64" placeholder="(Optional)" autocomplete="off">
                        <br><br>
                        <div class="form-row">
                            <div class="col-sm-5 mb-2">
                                <label><small>Who can see posts</small></label>
                                <select v-model="pagePrivacy" class="custom-select custom-select-sm mr-sm-2" required>
                                    <option value="1">Public (Everyone)</option>
                                    <option value="0">Private (Subscribers)</option>
                                </select>
                            </div>
                            <div class="col-sm-5">
                                <label><small>Who can post</small></label>
                                <select v-model="pagePermissions" class="custom-select custom-select-sm mr-sm-2" required>
                                    <option value="1">Subscribers</option>
                                    <option value="0">Only me</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <span><small>Maximum 3 per user</small>&emsp;</span>
                        <button type="button" class="btn btn-secondary modal-btn" data-dismiss="modal">Cancel</button>
                        <button ref="createBtn" @click="create" :class="{'not-allowed': turnRed || !pageName}" type="button" class="btn btn-primary modal-btn" disabled>Create</button>
                    </div>
                </div>
            </div>
        </div>`
    ),
    methods: {
        pageNameValidChars() {
            this.turnRed = false;
            this.smallPageNameText = this.defaultText;
            const check = !!this.pageName.match(/^[a-z0-9_]+$/i);    // Check if all characters are valid
            this.$refs.createBtn.disabled = !check;
            if (!check) this.invalidateForm();
            return check;
        },
        invalidateForm(message=null) {
            this.smallPageNameText = message ? message : this.defaultText;
            this.$refs.createBtn.disabled = true;
            this.turnRed = !!this.pageName;    // Don't turn red if field is empty
        },
        pageNameTaken() {    // Prevents a frenzy of requests with the same page name
            const taken = this.TAKEN_PAGE_NAMES.includes(this.pageName.toLowerCase());
            if (taken) this.invalidateForm(this.nameTakenText);
            return taken;
        },
        validateForm() {
            return this.pageNameValidChars() && !this.pageNameTaken() && (this.pagePrivacy == 0 || this.pagePrivacy == 1) && (this.pagePermissions == 0 || this.pagePermissions == 1);
        },
        create() {
            if (this.validateForm()) {
                data = new FormData();
                data.set("name", this.pageName);
                data.set("displayName", this.pageDisplayName);
                data.set("privacy", this.pagePrivacy);
                data.set("permissions", this.pagePermissions);

                axios.post("/newPage", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                    .then(res => {
                        if (res.data["s"]) {
                            window.location = `/page/${res.data["name"]}`;
                        } else {
                            if (res.data["m"] === this.nameTakenText) this.TAKEN_PAGE_NAMES.push(data.get("name").toLowerCase());
                            this.invalidateForm(res.data["m"]);
                        }
                    })
                    .catch(err => display_error(err));
            }
        }
    }
}

const NewPageInstance = PN.startsWith("/profile") ? new Vue({
    el: "#new-page-form",
    components: {"new-page-modal": NewPageComponent}
}) : undefined;
