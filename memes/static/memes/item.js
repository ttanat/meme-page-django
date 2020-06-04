document.querySelector("#page").textContent = "Meme";
const UUID = document.querySelector(".item").dataset.uuid;
const num_comments_span = document.querySelector("#num-comments");
if (window.location.hash === "#comments") document.querySelector(num_comments_span.textContent > 3 ? "#item-mid-ad" : "#comments").scrollIntoView({behavior: "smooth"});

// Supported image types for comments
const comment_img_types = Object.freeze(["image/jpeg", "image/png", "image/gif"]);

const VoteButtonsComponent = {
    props: {
        pts: {
            type: Number,
            required: true
        }
    },
    mounted() {
        if (AUTH) {
            axios.get(`/api/likes/m/?u=${UUID}`)
                .then(res => {
                    if (res.data.length) {
                        this.isLiked = res["data"][0]["point"] === 1;
                        this.isDisliked = res["data"][0]["point"] === -1;
                    }
                })
                .catch(console.log);
        }
    },
    data() {
        return {
            isLiked: false,
            isDisliked: false,
            meme: {
                points: this.pts,
                uuid: UUID
            }
        }
    },
    template: (
        `<div style="padding-right: 20px;">
            <button @click="vote('l')" :class="{green: isLiked}" class="btn btn-sm lower-btn thumbs like">
                <i :class="[isLiked ? 'fas' : 'far']" class="fa-thumbs-up"></i>
            </button>
            <span class="text-muted">{{ meme.points }} point{{ meme.points === 1 ? "" : "s" }}</span>
            <button @click="vote('d')" :class="{red: isDisliked}" class="btn btn-sm lower-btn thumbs dislike ml-3">
                <i :class="[isDisliked ? 'fas' : 'far']" class="fa-thumbs-down"></i>
            </button>
        </div>`
    ),
    methods: {
        vote(v) {
            voteAction(this, this.meme, v, "m")
        }
    }
}

const VoteButtons = new Vue({el: "#vote-btns", components: {"vote-buttons-td": VoteButtonsComponent}})

const NC = Object.freeze({username: USERNAME, points: 0, num_replies: 0, dp_url: DP_URL});
const NR = Object.freeze({username: USERNAME, points: 0, dp_url: DP_URL});

const ReplyComponent = {
    props: {
        reply: {
            type: Object,
            required: true
        }
    },
    mounted() {
        if (this.reply.image) this.$emit("new-reply-loaded-event", this.$refs.replyImg);
    },
    data() {
        return {
            isLiked: false,
            isDisliked: false,
            editing: false,
            hidePoints: this.reply.points === null,
            typingReply: false,
            replyInputValue: "",
            replyInputPlaceholder: "Write a reply",
            imageFilename: ""
        }
    },
    computed: {
        isAuthenticated() {
            return AUTH
        },
        isOwnReply() {
            return this.reply.username === USERNAME
        },
        hasDP() {
            return DP_URL
        },
        timesince() {
            return formatDate(this.reply.post_date)
        },
        rpattern() {
            return this.reply.content.match(/^@([a-z0-9_]+) /i)
        },
        replyAfterMention() {
            return this.reply.content.slice(this.reply.content.indexOf(" "))
        },
        displayPoints() {
            return this.reply.points && !this.hidePoints ? this.reply.points : ""
        },
        isDeleted() {
            return !this.reply.content && !this.reply.image
        }
    },
    template: (
        `<div :class="{'mb-2': isDeleted}" class="container-fluid">
            <div class="row">
                <div class="reply-left-column">
                    <a :href="'/user/'+reply.username"><img v-if="reply.dp_url" class="rounded-circle" :src="reply.dp_url" height="25" width="25"><i v-else class="fas fa-user-circle"></i></a>
                </div>
                <div class="reply-right-column" :style="{paddingTop: reply.dp_url ? '3px' : ''}">
                    <span><a :href="'/user/'+reply.username" class="comment-username">{{ reply.username }}</a>&ensp;<span class="comment-date">{{ timesince }}{{ reply.edited ? " (edited)" : "" }}</span></span>
                    <div v-if="isAuthenticated && !isDeleted" class="dropdown comment-down-btn float-right">
                        <span data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                            <i class="fas fa-angle-down"></i>
                        </span>
                        <div class="dropdown-menu dropdown-menu-right c-dropdown-menu">
                            <template v-if="isAuthenticated && isOwnReply">
                                <div class="dropdown-item" ref="toggleEditButton" @click="toggleEdit"><template v-if="editing"><i class="fas fa-times"></i>&ensp;Cancel</template><template v-else><i class="fas fa-pen"></i>&ensp;Edit</template></div>
                                <div class="dropdown-item" @click="confirmDelete"><i class="fas fa-trash-alt"></i>&ensp;Delete</div>
                            </template>
                            <div v-else class="dropdown-item"><i class="fas fa-flag"></i>&ensp;Report</div>
                        </div>
                    </div>
                    <br>
                    <span v-if="isDeleted" class="comment-deleted">Comment has been REDACTED</span>
                    <span v-else v-show="!editing" :class="{'d-block': !editing}" class="comment-content reply-content">
                        <span v-if="rpattern"><a :href="'/user/'+rpattern[1]">{{ rpattern[0] }}</a>{{ replyAfterMention }}</span>
                        <template v-else>{{ reply.content }}</template>
                    </span>
                    <input v-if="!isDeleted" v-show="editing && isAuthenticated && isOwnReply" ref="editReplyInput" @keyup.enter="editReply(reply.uuid)" class="edit-comment-field" :value="reply.content">
                    <a v-if="reply.image" :href="'/img?c='+reply.uuid" target="_blank">
                        <picture ref="replyImg">
                            <source :data-src="reply.image"></source>
                            <img class="mt-1 reply-image" data-src="/media/users/john/profile/ivz59jjdeht31.jpg">
                        </picture>
                    </a>

                    <div v-if="!isDeleted" class="container-fluid">
                        <div class="row comment-buttons">
                            <button @click="vote('l')" :class="{green: isLiked}" class="btn btn-sm c-thumbs like"><i :class="[isLiked ? 'fas' : 'far']" class="fa-thumbs-up"></i></button>
                            <button class="btn btn-sm comment-points text-muted" style="cursor: text;">{{ displayPoints }}</button>
                            <button @click="vote('d')" :class="{red: isDisliked}" class="btn btn-sm c-thumbs dislike ml-2"><i :class="[isDisliked ? 'fas' : 'far']" class="fa-thumbs-down"></i></button>
                            <button @click="typeReply" class="btn btn-sm text-muted reply-button">{{ typingReply ? "Close" : "Reply" }}</button>
                        </div>
                    </div>
                    <div v-if="!isDeleted" v-show="typingReply && isAuthenticated" class="container-fluid">
                        <div class="row">
                            <img v-if="hasDP" :src="hasDP" class="reply-field-dp rounded-circle" height="23" width="23" style="padding: 0;"><i v-else class="fas fa-user-circle reply-field-dp" style="font-size: 23px;"></i>
                            <input ref="replyInput" v-model.trim="replyInputValue" :placeholder="replyInputPlaceholder" :class="{'mb-2': !imageFilename}" class="reply-field reply-reply-field" type="text" maxlength="150" name="reply">
                            <a href="javascript:void(0);" @click="openImageInput" class="rf-img"><i class="far fa-image"></i></a><button @click="submitReply" class="btn btn-xs btn-primary r-post-btn" style="height: 27px;">Post</button>
                            <input ref="imageInput" @change="addReplyImage" type="file" accept="image/jpeg, image/png, image/gif" class="d-none">
                            <span v-if="imageFilename" class="mt-1 mb-2" style="margin-left: 33px;"><span>{{ imageFilename }}</span><a @click="removeReplyImage" class="ml-2" href="javascript:void(0);" style="color: red;"><i class="fas fa-times"></i></a></span>
                        </div>
                    </div>
                </div>
            </div>
        </div>`
    ),
    methods: {
        toggleEdit() {
            this.editing = !this.editing;
            if (this.editing) this.$nextTick(() => this.$refs.editReplyInput.focus());
        },
        confirmDelete() {
            $("#deleteModal")[0].querySelector(".modal-body").querySelector("span").textContent = "reply";
            $("#deleteModal")[0].querySelector("#deleteModalBtn").onclick = () => {
                this.deleteReply();
                $("#deleteModal").modal('hide')
            }
            $("#deleteModal").modal('show')
        },
        deleteReply() {
            axios.delete(`/comment/delete?u=${this.reply.uuid}`, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                .then(res => {
                    if (res.status === 204) this.$emit("reply-deleted-event", this.reply.uuid);
                })
                .catch(err => display_error(err));
        },
        editReply(uuid) {
            const val = event.target.value.slice(0, 150).trim();
            this.toggleEdit(uuid);
            if (AUTH && val.length && val !== this.reply.content) {
                const data = new FormData();
                data.set("c", val);
                data.set("u", uuid);
                axios.post("/comment/edit", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                .then(res => this.$emit("reply-edited-event", uuid, val))
                .catch(err => display_error(err));
            }
        },
        vote(v) {voteAction(this, this.reply, v, "c", this.hidePoints)},
        typeReply() {
            if (checkAuth()) {
                this.typingReply = !this.typingReply;
                if (this.typingReply) {
                    if (!this.replyInputValue) this.replyInputValue = `@${this.reply.username} `;
                    this.$nextTick(() => this.$refs.replyInput.focus());
                }
            }
        },
        submitReply() {
            if (!this.replyInputValue || !AUTH) return false;
            const r_input = this.$refs.replyInput;
            const data = new FormData();
            const val = this.replyInputValue.slice(0, 150).trim();
            if (val && val.length > 0 && val.match(/\S+/)) data.set("r", val);
            const img = this.imageInputValid() ? this.$refs.imageInput.files[0] : null;
            if (img) data.set("i", img);

            if (data.has("r") || data.has("i")) {
                const c_uuid = this.$parent.comment.uuid;
                data.set("c_uuid", c_uuid);
                this.replyInputValue = "";
                this.replyInputPlaceholder = "Sending...";

                axios.post("/reply", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                    .then(res => res.data)
                    .then(response => {
                        this.typingReply = false;
                        this.removeReplyImage();
                        this.$emit("reply-event", Object.assign(response, {c_uuid, post_date: new Date().toISOString(), content: val, image: data.has("i") ? URL.createObjectURL(img) : null}, NR));
                    })
                    .catch(err => {
                        display_error(err);
                        this.replyInputValue = val;
                    })
                    .finally(() => this.replyInputPlaceholder = "Write a reply");
            }
        },
        openImageInput() {
            this.$refs.imageInput.click();
        },
        imageInputValid() {
            const input = this.$refs.imageInput;
            return input.files.length === 1 && comment_img_types.includes(input.files[0].type);
        },
        addReplyImage() {
            this.imageInputValid() ? this.imageFilename = this.$refs.imageInput.files[0].name : this.removeReplyImage();
        },
        removeReplyImage() {
            this.imageFilename = "";
            this.$refs.imageInput.value = null;
        }
    }
}

const CommentComponent = {
    props: {
        comment: {
            type: Object,
            required: true
        }
    },
    components: {
        "reply-items": ReplyComponent
    },
    mounted() {
        if (this.comment.image) this.$emit("new-comment-loaded-event", this.$refs.commentImg);
    },
    data() {
        return {
            rdata: [],
            cmnt: this.comment,
            isLiked: false,
            isDisliked: false,
            editing: false,
            hidePoints: this.comment.points === null,
            showingReplies: false,
            loadMoreBtnShowing: false,
            loadSpinnerShowing: false,
            repliesAPILink: `/api/replies/?u=${this.comment.uuid}`,
            typingReply: false,
            replyInputValue: "",
            replyInputPlaceholder: "Write a reply",
            imageFilename: "",
            lazyReplyObserver: new IntersectionObserver(lazyLoad),
        }
    },
    computed: {
        isAuthenticated() {
            return AUTH;
        },
        isOwnComment() {
            return this.comment.username === USERNAME;
        },
        hasDP() {
            return DP_URL;
        },
        timesince() {
            return formatDate(this.comment.post_date);
        },
        displayPoints() {
            return this.comment.points && !this.hidePoints ? this.comment.points : "";
        },
        isDeleted() {
            return !this.comment.content && !this.comment.image
        }
    },
    template: (
        `<div class="comment">
            <div class="container-fluid">
                <div class="row">
                    <div class="comment-left-column">
                        <a :href="'/user/'+comment.username"><img v-if="comment.dp_url" class="rounded-circle" :src="comment.dp_url" height="40" width="40"><i v-else class="fas fa-user-circle"></i></a>
                    </div>
                    <div class="comment-right-column" :style="{paddingTop: comment.dp_url ? '10px' : '5px'}">
                        <div>
                            <span><a :href="'/user/'+comment.username" class="comment-username">{{ comment.username }}</a>&ensp;<span class="comment-date">{{ timesince }}{{ comment.edited ? " (edited)" : "" }}</span></span>
                            <div v-if="isAuthenticated && !isDeleted" class="dropdown comment-down-btn float-right">
                                <span data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                    <i class="fas fa-angle-down"></i>
                                </span>
                                <div class="dropdown-menu dropdown-menu-right c-dropdown-menu">
                                    <template v-if="isOwnComment">
                                        <div class="dropdown-item" @click="toggleEdit" ref="toggleEditButton"><template v-if="editing"><i class="fas fa-times"></i>&ensp;Cancel</template><template v-else><i class="fas fa-pen"></i>&ensp;Edit</template></div>
                                        <div class="dropdown-item" @click="confirmDelete"><i class="fas fa-trash-alt"></i>&ensp;Delete</div>
                                    </template>
                                    <div v-else class="dropdown-item"><i class="fas fa-flag"></i>&ensp;Report</div>
                                </div>
                            </div>
                        </div>
                        <span v-show="!editing" :class="{'d-block': !editing, 'comment-deleted': isDeleted}" class="comment-content mr-2">{{ isDeleted ? "Comment has been REDACTED" : comment.content }}</span>
                        <input v-if="!isDeleted" v-show="editing && isAuthenticated && isOwnComment" ref="editCommentInput" @keyup.enter="editComment(comment.uuid)" class="edit-comment-field" :value="comment.content">
                        <a v-if="comment.image" :href="'/img?c='+comment.uuid" target="_blank">
                            <picture ref="commentImg">
                                <source :data-src="comment.image"></source>
                                <img class="mt-1 comment-image" data-src="/media/users/john/profile/ivz59jjdeht31.jpg">
                            </picture>
                        </a>

                        <div v-if="!isDeleted" class="container-fluid">
                            <div class="row comment-buttons">
                                <button @click="vote('l')" :class="{green: isLiked}" class="btn btn-sm c-thumbs like mr-0"><i :class="[isLiked ? 'fas' : 'far']" class="fa-thumbs-up" style="margin-left: 0;"></i></button>
                                <button class="btn btn-sm comment-points" style="cursor: text;">{{ displayPoints }}</button>
                                <button @click="vote('d')" :class="{red: isDisliked}" class="btn btn-sm c-thumbs dislike ml-2"><i :class="[isDisliked ? 'fas' : 'far']" class="fa-thumbs-down"></i></button>
                                <button @click="typeReply" class="btn btn-sm reply-button">{{ typingReply ? "Close" : "Reply" }}</button>
                            </div>
                        </div>
                        <div v-if="comment.num_replies">
                            <small @click="viewReplies" class="comment-small">
                                {{ showingReplies ? "Hide" : "View" }} {{ comment.num_replies === 1 ? "reply" : comment.num_replies + " replies" }} <i :class="[showingReplies ? 'fa-caret-up' : 'fa-caret-down']" class="fas"></i>
                            </small>
                            <br>
                            <div v-show="showingReplies">
                                <reply-items v-for="reply in rdata" :key="reply.uuid" :reply="reply" @reply-event="replyAdded" @new-reply-loaded-event="observeNewReply" @reply-edited-event="replyEdited" @reply-deleted-event="replyDeleted"></reply-items>
                            </div>
                            <div v-if="loadMoreBtnShowing && showingReplies"><small class="comment-small" @click="loadReplies">Load more <i class="fas fa-angle-right"></i></small></div>
                            <div v-show="loadSpinnerShowing" style="font-size: 20px;"><i class="fas fa-circle-notch fa-spin"></i></div>
                        </div>
                        <div v-if="!isDeleted" v-show="typingReply && isAuthenticated" class="container-fluid">
                            <div class="row">
                                <img v-if="hasDP" :src="hasDP" class="reply-field-dp rounded-circle" height="25" width="25"><i v-else class="fas fa-user-circle reply-field-dp" style="font-size: 25px;"></i>
                                <input ref="replyInput" v-model.trim="replyInputValue" :placeholder="replyInputPlaceholder" class="reply-field" type="text" maxlength="150" name="reply">
                                <a href="javascript:void(0);" @click="openImageInput" class="rf-img"><i class="far fa-image"></i></a><button @click="submitReply" class="btn btn-xs btn-primary r-post-btn">Post</button>
                                <input ref="imageInput" @change="addReplyImage" type="file" accept="image/jpeg, image/png, image/gif" class="d-none">
                                <span v-if="imageFilename" class="mt-1" style="margin-left: 35px;"><span>{{ imageFilename }}</span><a @click="removeReplyImage" class="ml-2" href="javascript:void(0);" style="color: red;"><i class="fas fa-times"></i></a></span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`
    ),
    methods: {
        observeNewReply(reply) {this.lazyReplyObserver.observe(reply)},
        toggleEdit() {
            this.editing = !this.editing;
            if (this.editing) this.$nextTick(() => this.$refs.editCommentInput.focus());
        },
        confirmDelete() {
            $("#deleteModal")[0].querySelector(".modal-body").querySelector("span").textContent = "comment";
            $("#deleteModal")[0].querySelector("#deleteModalBtn").onclick = () => {
                this.deleteComment();
                $("#deleteModal").modal('hide');
            };
            $("#deleteModal").modal('show');
        },
        deleteComment() {
            axios.delete(`/comment/delete?u=${this.comment.uuid}`, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                .then(res => {
                    if (res.status === 204) this.$emit("comment-deleted-event", this.comment.uuid);
                })
                .catch(err => display_error(err));
        },
        editComment(uuid) {
            const val = this.$refs.editCommentInput.value.slice(0, 150).trim();
            this.toggleEdit(uuid);
            if (!AUTH || !val.length || val === this.comment.content) return false;
            const data = new FormData();
            data.set("c", val);
            data.set("u", uuid);
            axios.post("/comment/edit", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                .then(res => this.$emit("comment-edited-event", uuid, val))
                .catch(err => display_error(err));
        },
        vote(v) {voteAction(this, this.comment, v, "c", this.hidePoints)},
        typeReply() {
            if (checkAuth()) {
                this.typingReply = !this.typingReply;
                if (this.typingReply) this.$nextTick(() => this.$refs.replyInput.focus());
            }
        },
        viewReplies() {
            this.showingReplies = !this.showingReplies;
            if (!this.rdata.length && this.showingReplies) this.loadReplies();
        },
        loadReplies() {
            if (!this.repliesAPILink) return false;
            this.loadSpinnerShowing = true;
            axios.get(this.repliesAPILink)
                .then(res => res.data)
                .then(response => {
                    const l_uuids = [];
                    for (r of response["results"]) {
                        if (this.rdata.findIndex(r2 => r2.uuid === r.uuid) === -1) {
                            this.rdata.push(r);
                            if (r.points !== null) l_uuids.push(r.uuid);
                        }
                    }
                    this.loadMoreBtnShowing = !!response["next"];
                    this.repliesAPILink = response["next"];
                    if (response["auth"] && AUTH && l_uuids.length) this.loadReplyLikes(l_uuids);
                })
                .catch(err => display_error(err))
                .finally(() => this.loadSpinnerShowing = false);
        },
        loadReplyLikes(uuids) {
            if (AUTH && uuids.length) {
                axios.get(`/api/likes/c/?${uuids.slice(0, 20).map(uuid => `u=${uuid}`).join("&")}`)
                    .then(res => {
                        for (vote of res.data) {
                            const i = this.$children.findIndex(c => c.reply.uuid === vote["uuid"]);
                            this.$children[i].isLiked = vote["point"] === 1;
                            this.$children[i].isDisliked = vote["point"] === -1;
                        }
                    })
                    .catch(err => console.log(err));
            }
        },
        submitReply() {
            const r_input = this.$refs.replyInput;
            const data = new FormData();
            const val = this.replyInputValue.slice(0, 150).trim();
            if (val && val.length > 0 && val.match(/\S+/)) data.set("r", val);
            const img = this.imageInputValid() ? this.$refs.imageInput.files[0] : null;
            if (img) data.set("i", img);
            if (AUTH && (data.has("r") || data.has("i"))) {
                data.set("c_uuid", this.comment.uuid);
                this.replyInputValue = "";
                this.replyInputPlaceholder = "Sending...";

                axios.post("/reply", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                    .then(res => res.data)
                    .then(response => {
                        this.typingReply = false;
                        this.removeReplyImage();
                        this.replyAdded(Object.assign(response, {c_uuid: this.comment.uuid, post_date: new Date().toISOString(), content: val, image: data.has("i") ? URL.createObjectURL(img) : null}, NR));
                    })
                    .catch(err => {
                        display_error(err);
                        this.replyInputValue = val;
                    })
                    .finally(() => this.replyInputPlaceholder = "Write a reply");
            }
        },
        replyAdded(data) {
            // Only add reply if it is the first or last reply
            if (!this.comment.num_replies || this.comment.num_replies === this.rdata.length) this.rdata.push(data);
            this.comment.num_replies++;
            num_comments_span.textContent++;
        },
        openImageInput() {
            this.$refs.imageInput.click();
        },
        imageInputValid() {
            const input = this.$refs.imageInput;
            return input.files.length === 1 && comment_img_types.includes(input.files[0].type);
        },
        addReplyImage() {
            this.imageInputValid() ? this.imageFilename = this.$refs.imageInput.files[0].name : this.removeReplyImage();
        },
        removeReplyImage() {
            this.imageFilename = "";
            this.$refs.imageInput.value = null;
        },
        getReply(uuid) {
            const i = this.rdata.findIndex(r => r.uuid === uuid);
            return this.rdata[i];
        },
        replyEdited(uuid, val) {
            const reply = this.getReply(uuid);
            reply.content = val;
            reply.edited = true;
        },
        replyDeleted(uuid) {
            const reply = this.getReply(uuid);
            // this.rdata.splice(i, 1);
            // this.comment.num_replies--;
            // num_comments_span.textContent--;
            reply.content = null;
            reply.image = null;
        }
    },
}

const CommentsInstance = new Vue({
    el: "#comments-container",
    components: {
        "comment-items": CommentComponent
    },
    data: {
        cdata: [],
        scrollObserver: null,
        scrollRoot: null,
        next: "",
        loading: false,
        lazyCommentObserver: new IntersectionObserver(lazyLoad)
    },
    mounted() {
        if (parseInt(num_comments_span.textContent)) {
            this.loadComments();
            createScrollObserver(this, this.loadComments);
        }
    },
    updated() {
        updateScrollObserver(this);
    },
    methods: {
        observeNewComment(comment) {
            this.lazyCommentObserver.observe(comment);
        },
        loadComments() {
            if (this.next === null) return false;
            this.loading = true;

            axios.get(this.next || `/api/comments/?u=${UUID}`)
                .then(res => res.data)
                .then(response => {
                    const l_uuids = [];
                    let offset = 0;
                    for (r of response["results"]) {
                        if (this.cdata.findIndex(c => c.uuid === r.uuid) === -1) {
                            this.cdata.push(r);
                            l_uuids.push(r.uuid);
                        } else {
                            offset++;
                        }
                    }
                    if (response["auth"] && AUTH && l_uuids.length) this.loadLikes(l_uuids);
                    this.next = response["next"];
                    if (offset) {
                        const url = new URL(this.next);
                        const old_offset = url.searchParams.get("offset");
                        url.searchParams.set("offset", offset + (parseInt(old_offset) || 0));
                        this.next = url.href;
                    }
                })
                .catch(err => display_error(err))
                .finally(() => this.loading = false);
        },
        loadLikes(uuids) {
            if (AUTH && uuids.length) {
                axios.get(`/api/likes/c/?${uuids.slice(0, 20).map(uuid => `u=${uuid}`).join("&")}`)
                    .then(res => {
                        for (vote of res.data) {
                            const i = this.$children.findIndex(c => c.comment.uuid === vote["uuid"]);
                            this.$children[i].isLiked = vote["point"] === 1;
                            this.$children[i].isDisliked = vote["point"] === -1;
                        }
                    })
                    .catch(err => console.log(err));
            }
        },
        getComment(uuid) {
            const i = this.cdata.findIndex(c => c.uuid === uuid);
            return this.cdata[i];
        },
        commentEdited(uuid, val) {
            const comment = this.getComment(uuid);
            comment.content = val;
            comment.edited = true;
        },
        commentDeleted(uuid) {
            const comment = this.getComment(uuid);
            // num_comments_span.textContent -= (1 + this.cdata[i].num_replies);
            // this.cdata.splice(i, 1);
            comment.content = null;
            comment.image = null;
        }
    }
})

const PostNewCommentComponent = {
    data() {
        return {
            commentContent: "",
            placeholder: "Write a comment here!",
            fname: "",
            hasComments: !!parseInt(num_comments_span.textContent)
        }
    },
    template: (
        `<div style="margin-bottom: 20px;">
            <textarea ref="textarea" v-model.trim="commentContent" @keydown.enter.prevent :placeholder="placeholder" class="form-control mb-2" maxlength="150" rows="2" id="comment-field"></textarea>
            <button @click="post" class="btn btn-sm btn-primary mr-2" id="post-comment">Post</button>
            <button @click="chooseFile" class="btn btn-sm btn-outline-secondary text-light mr-2"><i class="far fa-image" style="font-size: 1rem;"></i></button>
            <input ref="inputFile" v-show="false" @change="showFname" id="post-comment-image" type="file" accept="image/jpeg, image/png, image/gif" autocomplete="off">
            <template v-if="fname"><span>{{ fname }}</span><a @click="removeFile" class="ml-2" id="remove-comment-img" href="javascript:void(0);" style="color: red;"><i class="fas fa-times"></i></a></template>
            <span class="text-muted float-right" style="font-size: 0.95rem;"><span ref="charsLeftSpan" id="chars-left">{{ 150 - commentContent.length }}</span> characters left</span>
            <div v-if="!hasComments" id="no-comments">No comments yet</div>
        </div>`
    ),
    methods: {
        post() {
            const data = new FormData();
            data.set("u", UUID);
            if (this.fileValid()) data.set("i", this.$refs.inputFile.files[0]);
            if (this.commentContent.length > 150) return false;
            const val = this.commentContent.slice(0, 150).trim();
            if (val && val.length > 0 && val.match(/\S+/)) data.set("c", val);

            if (checkAuth() && (data.has("c") || data.has("i"))) {
                this.commentContent = "";
                this.placeholder = "Sending...";

                axios.post("/comment/post", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                    .then(res => res.data)
                    .then(response => {
                        this.removeFile();
                        this.placeholder = "Sent";
                        setTimeout(() => {this.placeholder = "Write a comment here!"}, 1000);
                        CommentsInstance.cdata.unshift(Object.assign(response, NC, {post_date: new Date().toISOString(), content: val, image: data.has("i") ? URL.createObjectURL(data.get("i")) : null}));
                        num_comments_span.textContent++;
                        this.hasComments = !!parseInt(num_comments_span.textContent);
                    })
                    .catch(err => {
                        display_error(err);
                        this.commentContent = val;
                        this.placeholder = "Write a comment here!";
                    });
            }
        },
        fileValid() {
            const input = this.$refs.inputFile;
            if (input.files.length !== 1) return false;
            if (!comment_img_types.includes(input.files[0].type)) {
                alert("Supported media types: JPG, PNG, GIF");
                return false;
            } else if (input.files[0].size > 3145728) {
                alert("Maximum file size: 3 MB");
                return false;
            } else {
                return true;
            }
        },
        chooseFile() {
            if (checkAuth()) this.$refs.inputFile.click();
        },
        showFname() {
            if (this.fileValid()) this.fname = this.$refs.inputFile.files[0].name;
        },
        removeFile() {
            this.fname = "";
            this.$refs.inputFile.value = null;
        }
    }
}

const PostNewComment = new Vue({el: "#new-comment-form", components: {"post-comment-fields": PostNewCommentComponent}})

document.querySelectorAll(".tag").forEach(t => {
    t.onclick = () => window.open(`/search?q=%23${t.dataset.name.slice(1)}`)
})

if (AUTH) {
    $("#deleteModal").on('hide.bs.modal', function (e) {
        e.target.querySelector("#deleteModalBtn").onclick = null;
    })
}

if (document.querySelector(".content").tagName === "IMG") {
    const overlay = document.querySelector("#overlay");
    const navClassList = document.querySelector("nav").classList;

    function overlayOn() {
        overlay.style.display = "block";
        navClassList.remove("sticky-top");
        if (!overlay.lastChild.src) overlay.lastChild.src = document.querySelector(".content").src;
    }

    function overlayOff() {
        overlay.style.display = "none";
        navClassList.add("sticky-top");
    }
}

function copy_link_item(button) {
    copy_link(UUID);
    button.innerHTML = `<i class='fas fa-check'></i> Copied`;
    setTimeout(() => button.innerHTML = `<i class='fas fa-link'></i> Copy Link`, 1500)
}
