function checkAuth() {
    if (!AUTH) $('#signUpModal').modal('show');
    return AUTH;
}

const PN = window.location.pathname;

// URL of profile picture
const DP_URL = AUTH && document.querySelector("#profile-image").querySelector("img") ? document.querySelector("#profile-image").querySelector("img").src : null;

$(function () {
    $('[data-toggle="tooltip"]').tooltip()
})

// Supported file types for memes
const SFT = Object.freeze(["image/jpeg", "image/png", "image/gif", "video/mp4", "video/quicktime"]);

function resizeMid() {
    const midClassList = document.querySelector("#mid").classList;
    if (window.innerWidth > 1400) {
        midClassList.remove("col-xl-6");
        midClassList.add("col-xl-5");
    } else {
        midClassList.remove("col-xl-5");
        midClassList.add("col-xl-6");
    }
}

const SearchInstance = new Vue({
    el: "#search-form",
    data: {
        query: PN === "/search" ? new URL(window.location.href).searchParams.get("q") : "",
        style: {
            height: "30px",
            border: "solid 1px #333",
            fontWeight: "350"
        },
        inputStyle: {
            width: "25rem",
            color: "gainsboro",
            backgroundColor: "#111",
            transition: "none"
        },
        buttonStyle: {
            backgroundColor: "#222",
            color: "grey"
        },
        placeholder: "Search",
        searchIconOpacity: .6
    },
    template: `<form method="GET" action="/search" @submit.prevent="check" ref="form">
                    <div class="input-group">
                        <input
                            ref="input"
                            id="search"
                            v-model.trim="query"
                            :style="[style, inputStyle]"
                            type="text"
                            name="q"
                            class="nav-item form-control ml-2"
                            :placeholder="placeholder"
                            @focus="changePlaceholder('memes, #tags, @users, ^pages')"
                            @blur="changePlaceholder('Search')"
                            maxlength="64"
                        >
                        <div class="input-group-append">
                            <button @mouseenter="changeOpacity(1)" @mouseleave="changeOpacity(.6)" :style="[style, buttonStyle]" class="input-group-text">
                                <svg :opacity="searchIconOpacity" viewBox="0 0 24 24" preserveAspectRatio="xMidYMid meet" focusable="false" fill="grey" height="20" width="20">
                                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                </form>`,
    methods: {
        changePlaceholder(val) {
            this.placeholder = val
        },
        changeOpacity(val) {
            this.searchIconOpacity = val
        },
        check() {
            this.$refs.input.value = this.query;
            if (this.query) this.$refs.form.submit();
        }
    }
})

function night() {
    if (AUTH) {
        const on = JSON.parse(localStorage.getItem("night"));
        document.querySelector("main").style.opacity = on ? 1 : 0.6;
        localStorage.setItem("night", !on);
        document.querySelector("#moon-icon").className = on ? "far fa-moon" : "fas fa-moon";
    }
}
// Set night mode on/off when page loads
if (AUTH) {
    night();
    night();
}

const UploadFormComponent = {
    data() {
        return {
            fname: "Choose File",
            page: "",
            category: "",
            caption: "",
            nsfw: "",
            tags: "",
            videoDuration: 99,
            canSubmit: false,
            uploading: false
        }
    },
    computed: {
        displayTags() {
            const tags = this.tags.match(/#[a-zA-Z]\w*/g);
            return tags ? tags.slice(0, 20).join(" ") : "";
        }
    },
    template: (
        `<div class="modal fade" id="uploadModal" tabindex="-1" role="dialog" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content text-light">
                    <div class="modal-header">
                        <h5 class="modal-title">Upload Meme</h5>
                    </div>
                    <div class="modal-body">
                        <div class="form-row">
                            <div class="col-sm-6">
                                <label>Upload to</label>
                                <select v-model="page" class="custom-select custom-select-sm mr-sm-2">
                                    <option value="" selected>Your memes</option>
                                </select>
                            </div>
                            <div class="col-sm-6">
                                <label>
                                    Category <span class="text-muted" style="font-size: 12px;"><i class="far fa-question-circle" data-toggle="tooltip" title="Let your meme be discovered in more places!"></i></span>
                                </label>
                                <select v-model="category" class="custom-select custom-select-sm mr-sm-2">
                                    <option value="">None</option>
                                    <option value="movies">Movies</option>
                                    <option value="tv-shows">TV Shows</option>
                                    <option value="gaming">Gaming</option>
                                    <option value="animals">Animals</option>
                                    <option value="internet">Internet</option>
                                    <option value="school">School</option>
                                    <option value="anime">Anime</option>
                                    <option value="celebrities">Celebrities</option>
                                    <option value="sports">Sports</option>
                                    <option value="football">Football</option>
                                    <option value="nba">NBA</option>
                                    <option value="nfl">NFL</option>
                                    <option value="news">News</option>
                                    <option value="university">University</option>
                                </select>
                            </div>
                        </div>
                        <br>
                        <label>Caption</label>
                        <br>
                        <input v-model.trim="caption" type="text" class="input-form" maxlength="100" placeholder="Caption" autocomplete="off">
                        <br>
                        <small id="uploadCaptionSmall">{{ 100 - caption.length }} characters left</small>
                        <div class="custom-file mt-3 mb-3">
                            <input ref="inputFile" @change="validateForm" type="file" class="custom-file-input" accept="image/jpeg, image/png, image/gif, video/mp4, video/quicktime" autocomplete="off" required>
                            <label class="custom-file-label">{{ fname }}</label>
                        </div>
                        <div class="custom-control custom-checkbox custom-checkbox-sm mb-3">
                            <input v-model="nsfw" type="checkbox" id="uploadNsfw" class="custom-control-input custom-control-input-sm" autocomplete="off">
                            <label for="uploadNsfw" class="custom-control-label" style="color: tomato;font-size: 15px;">NSFW</label>
                        </div>
                        <textarea v-model="tags" class="form-control" rows="2" placeholder="#tags (optional)" autocomplete="off" style="resize: none;padding: .15em;padding-left: 4px;"></textarea>
                        <div style="color: royalblue;">{{ displayTags }}</div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary modal-btn" data-dismiss="modal" title="Cancel">Cancel</button>
                        <button ref="submitButton" @click="upload" :class="{'not-allowed': !canSubmit}" type="button" class="btn btn-primary modal-btn" title="Upload" disabled>
                            <template v-if="uploading">Uploading <i class="fas fa-circle-notch fa-spin"></i></template><template v-else>Upload</template>
                        </button>
                    </div>
                </div>
            </div>
        </div>`
    ),
    methods: {
        validateForm() {
            const uf = this.$refs.inputFile;
            this.canSubmit = uf.files.length === 1 && ["image/jpeg", "image/png", "image/gif", "video/mp4", "video/quicktime"].includes(uf.files[0].type);
            uf.files[0].type.startsWith("video/") ? this.setVidDuration(uf.files[0]) : this.videoDuration = 99;
            this.$refs.submitButton.disabled = !this.canSubmit;
            this.fname = this.canSubmit ? uf.files[0].name : "Choose File";
            if (!this.canSubmit) uf.value = null;
        },
        setVidDuration(file) {
            const v = document.createElement("video");
            v.preload = "metadata";
            v.onloadedmetadata = () => {
                URL.revokeObjectURL(v.src);
                this.videoDuration = v.duration;
            }
            v.src = URL.createObjectURL(file);
        },
        check() {
            const input = this.$refs.inputFile;
            const file = input.files[0];
            const type = file.type;
            const lfname = file.name.toLowerCase();
            type.startsWith("video/") ? this.setVidDuration(file) : this.videoDuration = 99;
            if (!file || !input.files.length) {
                alert("Please select a file.");
            } else if (input.files.length > 1) {
                alert("Cannot upload multiple files together.");
            } else if (!SFT.includes(type) || (type === "image/jpeg" && (!lfname.endsWith(".jpg") && !lfname.endsWith(".jpeg"))) || (type === "video/quicktime" && !lfname.endsWith(".mov"))) {
                alert("Supported media types: JPG, PNG, GIF, MP4, MOV");
            } else if (type === "image/gif" && file.size > 5242880) {
                alert("Maximum file size for GIF is 5 MB");
            } else if (type.startsWith("image/") && file.size > 3145728) {
                alert("Maximum file size for images is 3 MB");
            } else if (type.startsWith("video/") && this.videoDuration > 60) {
                alert("Maximum video duration is 60 seconds");
            } else if (type.startsWith("video/") && file.size > 15728640) {
                alert("Maximum file size for videos is 15 MB");
            } else {
                return true;
            }
            return false;
        },
        setData() {
            const d = new FormData();
            d.set("file", this.$refs.inputFile.files[0]);
            if (this.page) d.set("page", this.page);
            if (this.category) d.set("category", this.category);
            if (this.caption) d.set("caption", this.caption.trim().slice(0, 100));
            if (!d.get("caption") && !confirm("Are you sure you want to upload without a caption?")) return null;
            const tags = this.tags.match(/#[a-zA-Z]\w*/g);
            if (tags) {
                for (let i = 0, n = tags.slice(0, 20).length; i < n; i++) {
                    d.append("tags", tags[i].slice(0, 64));
                }
            }
            d.set("nsfw", this.nsfw);
            return d;
        },
        upload() {
            if (!AUTH || !this.check()) return false;
            const data = this.setData();
            if (!data || !data.has("file")) return false;
            if (PN === "/profile") data.set("is_profile_page", true);
            if (PN.startsWith("/page/")) data.set("is_meme_page", true);
            this.$refs.submitButton.disabled = true;
            this.$refs.submitButton.style.cursor = "progress";
            this.uploading = true;
            axios.post("/upload", data, {headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"}})
                .then(res => res.data)
                .then(response => {
                    if (response["s"]) {
                        display_success("Meme successfully uploaded.");
                        $("#uploadModal").modal("hide");
                        // Tell vue component that content_type is PNG so that GIF is displayed in IMG tag
                        const tile_data = {uuid: response.uuid, url: URL.createObjectURL(data.get("file")), content_type: data.get("file").type === "image/gif" ? "image/png" : data.get("file").type};
                        if (PN === "/profile" && TilesInstance) {
                            TilesInstance.tiles.unshift(tile_data);
                        } else if (MemesInstance) {
                            const meme_data = Object.assign(tile_data, {username: USERNAME, caption: data.get("caption"), points: 0, num_comments: 0, dp_url: DP_URL});
                            if (PN === `/page/${data.get("page")}`) {
                                MemesInstance.mdata.unshift(Object.assign(meme_data, {pname: data.get("page"), pdname: PAGE_DNAME ? PAGE_DNAME : null}));
                            } else if (PN === "/all") {
                                MemesInstance.mdata.unshift(meme_data);
                            }
                        }
                        this.page = this.category = this.caption = this.nsfw = this.tags = "";
                        this.$refs.inputFile.value = null;
                        this.fname = "Choose File";
                    } else {
                        alert(response["m"]);
                    }
                })
                .catch(err => display_error(err))
                .finally(() => this.uploading = this.canSubmit = false);
        }
    }
}

const UploadFormInstance = AUTH ? new Vue({
    el: "#upload-form",
    components: {"upload-modal": UploadFormComponent}
}) : undefined;

// Drag and drop memes
const main = document.querySelector("main");
main.ondragover = main.ondragenter = () => false;
main.ondrop = (e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    const type = files[0].type;
    if (!type) return false;
    if (files.length > 1) {
        alert("Cannot upload multiple files together.");
    } else if (!SFT.includes(type) || (type === "video/quicktime" && !files[0].name.endsWith(".mov"))) {
        alert("Supported media types: JPG, PNG, GIF, MP4, MOV");
    } else {
        UploadFormInstance.$children[0].$refs.inputFile.files = files;
        UploadFormInstance.$children[0].validateForm();
        $("#uploadModal").modal("show");
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

document.querySelectorAll(".content, .m-dropdown, [data-toggle='tooltip']").forEach(el => {
    el.oncontextmenu = () => false
})

function copy_link(uuid) {
    const copy_text = document.querySelector("#copy_text");
    copy_text.style.display = "";
    copy_text.value = `${window.location.origin}/m/${uuid}`;
    copy_text.select();
    document.execCommand("cut");
    copy_text.style.display = "none";
}

function formatDate(timestring) {
    const min = (new Date() - new Date(timestring)) / 1000 / 60;
    if (min < 1) return `${Math.round(s)} second${Math.round(s) === 1 ? "" : "s"}`;
    const hrs = min / 60;
    if (hrs < 1) return `${Math.round(min)} minute${Math.round(min) === 1 ? "" : "s"}`;
    const days = hrs / 24;
    if (days < 1) return `${Math.round(hrs)} hour${Math.round(hrs) === 1 ? "" : "s"}`;
    const wks = days / 7;
    if (wks < 1) return `${Math.round(days)} day${Math.round(days) === 1 ? "" : "s"}`;
    const mnths = days / 30;
    if (mnths < 1) return `${Math.round(wks)} week${Math.round(wks) === 1 ? "" : "s"}`;
    const yrs = days / 365;
    if (yrs < 1) return `${Math.round(mnths)} month${Math.round(mnths) === 1 ? "" : "s"}`;
    return `${Math.round(yrs)} year${Math.round(yrs) === 1 ? "" : "s"}`;
}

// function toBlob(n=0) {
//     setTimeout(() => {
//         document.querySelectorAll("[data-src]").forEach(el => {
//             axios.get(el.dataset.src, {responseType: "blob"})
//                 .then(res => res.data)
//                 .then(response => {
//                     el.onload = () => {
//                         URL.revokeObjectURL(el.src);
//                         el.removeAttribute("data-src");
//                     }
//                     el.src = URL.createObjectURL(response);
//                 })
//         })
//     }, n);
// }

window.addEventListener("blur", () => {
    document.querySelectorAll(".autoplay").forEach(a => {
        MemesInstance.$children.forEach(c => {
            if (c.isVideo) c.togglePlayback(false);
        })
    })
})

function lazyLoad(entries, observer) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const lazyEl = entry.target;
            for (el of lazyEl.children) {
                if (lazyEl.tagName === "PICTURE" && el.tagName === "SOURCE") {
                    el.srcset = el.dataset.src;
                } else if (el.tagName === "SOURCE" || el.tagName === "IMG") {
                    el.src = el.dataset.src;
                }
                el.removeAttribute("data-src");
            }
            lazyEl.onloadeddata = () => {
                // Video sometimes doesn't play if it is the first meme at top of page due to AbortError
                if (entry.intersectionRatio > 0.9) lazyEl.play()
            }
            if (lazyEl.tagName === "VIDEO") lazyEl.load();
            observer.unobserve(lazyEl);
        }
    })
}

function createScrollObserver(inst, load) {
    /* Takes in vue instance (inst) and its method for loading more content (load) */
    /* Called when instance is mounted */
    inst.scrollObserver = new IntersectionObserver(([entry]) => {
        if (entry.isIntersecting && inst.next !== null) {
            load();
            inst.next = null;   // Prevent loading same page more than once
        }
    })
}

function updateScrollObserver(inst) {
    /* Takes in vue instance (inst) */
    /* Called when new content loaded */
    /* Finds the last child element and observe it */
    /* Loads more content when scrolling reaches this element */
    if (inst.scrollObserver) {
        if (inst.scrollRoot) inst.scrollObserver.unobserve(inst.scrollRoot);
        if (inst.$children.length && inst.next !== null) {
            inst.scrollRoot = inst.$children[inst.$children.length - 1].$el;
            inst.scrollObserver.observe(inst.scrollRoot);
        }
    }
}

function voteAction(inst, item, v, t, hide=false) {
    if (checkAuth()) {
        const old_state = [inst.isLiked, inst.isDisliked, item.points];
        var btn;
        if (v === "l") {
            inst.isLiked = !inst.isLiked;
            if (inst.isLiked && inst.isDisliked) inst.isDisliked = false;
            if (!hide) item.points += inst.isLiked && old_state[1] ? 2 : inst.isLiked ? 1 : -1;
            btn = inst.isLiked;
        } else if (v === "d") {
            inst.isDisliked = !inst.isDisliked;
            if (inst.isLiked && inst.isDisliked) inst.isLiked = false;
            if (!hide) item.points -= inst.isDisliked && old_state[0] ? 2 : inst.isDisliked ? 1 : -1;
            btn = inst.isDisliked;
        }

        axios({
            method: btn ? "PUT" : "DELETE",
            url: "/like",
            headers: {"X-CSRFToken": getCookie('csrftoken'), "X-Requested-With": "XMLHttpRequest"},
            params: {u: item.uuid, t, v}
        })
            .catch(err => {
                display_error(err);
                inst.isLiked = old_state[0];
                inst.isDisliked = old_state[1];
                if (!hide) item.points = old_state[2];
            });
    }
}

const MemeComponent = {
    props: {
        meme: {
            type: Object,
            required: true
        },
        muted: {
            type: Boolean,
            required: true
        }
    },
    data() {
        return {
            isLiked: false,
            isDisliked: false,
            isVideo: this.meme.content_type.startsWith('video/') || this.meme.content_type === "image/gif",
            isGif: this.meme.content_type === "image/gif",
            paused: true,
            itemStyle: {
                backgroundColor: "#191919",
                borderTop: "solid 1px #333",
                borderBottom: "solid 1px #333"
            },
            headerStyle: {
                paddingLeft: "10px",
                paddingRight: "10px",
                paddingTop: "5px"
            },
            headerAStyle: {
                fontSize: "14px",
                color: "darkgrey"
            },
            headerPageStyle: {
                fontSize: "13px",
                color: "grey"
            },
            bodyStyle: {
                maxHeight: "30rem",
                // maxHeight: "80vh",
                position: "relative"
            },
            bodyAStyle: {
                maxHeight: "inherit"
            },
            contentStyle: {
                width: "100%",
                marginBottom: "0",
                maxHeight: "inherit",
                objectFit: "contain"
            },
            playCircleStyle: {
                position: "absolute",
                top: "0",
                bottom: "0",
                left: "0",
                right: "0",
                margin: "auto",
                opacity: ".7",
                backgroundColor: "black",
                height: "5rem",
                width: "5rem",
                textAlign: "center",
                paddingTop: "1.75rem",
                cursor: "pointer"
            },
            playIconStyle:{
                fontSize: "1.5rem"
            },
            soundToggleStyle: {
                position: "absolute",
                right: ".5rem",
                bottom: ".5rem",
                fontSize: "1.25rem",
                cursor: "pointer",
                textShadow: ".1rem .1rem .2rem #111"
            }
        }
    },
    mounted() {
        this.$emit("new-meme-event", this.isVideo ? this.$refs.vidMeme : this.$refs.imgMeme, this.isVideo);
    },
    template: (
        `<div class="item" :style="itemStyle">
            <div :style="headerStyle">
                <a :href="'/user/' + meme.username" :style="headerAStyle"><img v-if="meme.dp_url" class="rounded-circle" :src="meme.dp_url" height="18" width="18"><i v-else class="fas fa-user-circle" style="font-size: 15px;"></i>&nbsp;{{ meme.username }}</a><template v-if="meme.pname"><span :style="headerPageStyle">&ensp;<i class="fas fa-caret-right"></i>&ensp;<a :href="'/page/'+meme.pname" :style="headerPageStyle">{{ meme.pdname || meme.pname }}</a></span></template>
                <br>
                <h6 class="mt-2" style="font-weight: 450;">{{ meme.caption }}</h6>
            </div>

            <div ref="cbody" @contextmenu.prevent :style="[bodyStyle, {backgroundColor: isVideo ? '#111' : ''}]" style="height: 80vh;">
                <template v-if="isVideo">
                    <a @click.prevent="vidClick" :href="'/m/'+meme.uuid" target="_blank" :style="bodyAStyle" draggable="false">
                        <video ref="vidMeme" @pause="togglePlayback(false)" @play="togglePlayback" :style="contentStyle" draggable="false" class="content autoplay" controlsList="nodownload" muted loop playsinline @loadeddata="rmCBodyHeight" style="max-height: 70vh;">
                            <source :data-src="meme.url"></source>
                        </video>
                    </a>
                    <div v-if="paused" @click="togglePlayback" class="rounded-circle" :style="[playCircleStyle, {paddingLeft: isGif ? '' : '.35rem'}]">
                        <h5 v-if="isGif">GIF</h5><i v-else class="fas fa-play" :style="playIconStyle"></i>
                    </div>
                    <i v-if="!isGif" @click="$emit('toggle-sound-event')" class="fas" :class="[muted ? 'fa-volume-mute' : 'fa-volume-up']" :style="soundToggleStyle"></i>
                </template>
                <a v-else :href="'/m/'+meme.uuid" target="_blank" :style="bodyAStyle" draggable="false">
                    <picture ref="imgMeme" class="content" :style="contentStyle">
                        <source :data-src="meme.url"></source>
                        <img @load="rmCBodyHeight" :style="contentStyle" draggable="false" data-src="/media/users/john/profile/ivz59jjdeht31.jpg" class="content" loading="lazy">
                    </picture>
                </a>
            </div>

            <table>
                <tr>
                    <td>
                        <button @click="vote('l')" :class="{green: isLiked}" class="btn btn-sm lower-btn thumbs like pr-0"><i :class="[isLiked ? 'fas' : 'far']" class="fa-thumbs-up"></i></button>
                        <span class="text-muted">&nbsp;<span class="points">{{ meme.points }}</span></span>
                    </td>
                    <td>
                        <button @click="vote('d')" :class="{red: isDisliked}" class="btn btn-sm lower-btn thumbs dislike"><i :class="[isDisliked ? 'fas' : 'far']" class="fa-thumbs-down"></i></button>
                    </td>
                    <td>
                        <a class="btn btn-sm lower-btn" :href="'/m/'+meme.uuid+'#comments'" target="_blank"><i class="far fa-comment"></i>&nbsp;{{ meme.num_comments }}</a>
                    </td>
                    <td v-if="isVideo">
                        <button @click="restartVid" class="btn btn-sm lower-btn" title="Restart playback"><i class="fas fa-undo"></i></button>
                    </td>
                    <td>
                        <div class="dropdown">
                            <button class="btn lower-btn" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                <i class="fas fa-ellipsis-h"></i>
                            </button>
                            <div class="dropdown-menu bg-dark" @contextmenu.prevent>
                                <a class="dropdown-item m-dropdown" :href="'/img?m='+meme.uuid" target="_blank"><i class="fas fa-download"></i> Download</a>
                                <div class="dropdown-item m-dropdown" @click="copyLink"><i class="fas fa-link"></i> Copy Link</div>
                                <div class="dropdown-item m-dropdown"><i class="fas fa-share"></i> Share</div>
                                <div class="dropdown-item m-dropdown"><i class="far fa-flag"></i> Report</div>
                            </div>
                        </div>
                    </td>
                </tr>
            </table>
        </div>`
    ),
    methods: {
        vidClick() {this.paused ? this.togglePlayback() : window.open(`/m/${this.meme.uuid}`)},
        togglePlayback(play=true) {
            this.paused = !play;
            play ? this.$refs.vidMeme.play() : this.$refs.vidMeme.pause();
        },
        rmCBodyHeight() {this.$refs.cbody.style.height = null},
        copyLink() {copy_link(this.meme.uuid)},
        vote(v) {voteAction(this, this.meme, v, "m")},
        restartVid() {this.$refs.vidMeme.currentTime = 0}
    }
}

const MemesInstance = document.querySelector("meme-items") ? new Vue({
    el: "#memes-container",
    components: {
        "meme-items": MemeComponent
    },
    data: {
        mdata: [],
        muted: true,
        scrollObserver: null,
        scrollRoot: null,
        next: "",
        loading: false,
        // Load media file when it is 300px from the viewport
        lazyMemeObserver: new IntersectionObserver(lazyLoad, {rootMargin: "300px 0px"}),
        autoplayObserver: null
    },
    mounted() {
        this.loadMemes();   // Initial load
        this.autoplayObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const i = this.$children.findIndex(c => c.$refs.vidMeme === entry.target);
                this.$children[i].togglePlayback(entry.intersectionRatio > 0.9);
            })
        }, {threshold: [0.1, 0.9]});
        createScrollObserver(this, this.loadMemes);
    },
    updated() {
        updateScrollObserver(this);
    },
    methods: {
        toggleSound() {
            this.muted = !this.muted;
            this.$children.forEach(c => {if (c.isVideo) c.$refs.vidMeme.muted = this.muted})
        },
        observeNewMeme(meme, isVideo) {
            this.lazyMemeObserver.observe(meme);
            if (isVideo) this.autoplayObserver.observe(meme);
        },
        loadMemes() {
            if (this.next === null || (PN.startsWith("/page/") && (!SHOW || !PAGE_NUM_POSTS))
                || (!["/", "/all", "/feed", "/search"].includes(PN) && !PN.match(/^\/page\/[a-zA-Z0-9_]+$/)
                && !PN.match(/^\/browse\/[a-zA-Z0-9_]+$|^\/browse\/tv-shows$/))) return false;
            this.loading = true;

            axios.get(this.getURL())
                .then(res => res.data)
                .then(response => {
                    const results = response["results"];
                    const l_uuids = [];
                    if (results.length) {
                        for (r of results) {
                            if (this.mdata.findIndex(m => m.uuid === r.uuid) === -1) {
                                this.mdata.push(r);
                                l_uuids.push(r.uuid);
                            }
                        }
                        if (response["auth"] && AUTH && l_uuids.length) this.loadLikes(l_uuids);
                        this.next = response["next"];
                    } else {
                        if (this.next === "" && !this.$children.length) {
                            const returnHome = 'Return <a href="/">home</a>';
                            const inside = PN === "/search" ? `No results matching query.<br><br>${returnHome}` : PN === "/feed" ? 'No new posts.<br><br>Subscribe to more pages or follow other users for more posts!' : `No memes here :(<br><br>${returnHome}`;
                            this.$el.innerHTML = `<div style="margin-top: 30px;text-align: center;">${inside}</div>`;
                        }
                        if (this.scrollRoot) this.scrollObserver.unobserve(this.scrollRoot);
                        this.scrollObserver = this.scrollRoot = this.next = null;
                    }
                })
                .catch(err => console.log(err))
                .finally(() => this.loading = false);
        },
        getURL() {
            return this.next || (PN === "/search" ? `/api/memes/?p=search&q=${encodeURIComponent(new URL(window.location.href).searchParams.get("q").slice(0, 64))}`
                 : PN.startsWith("/page/") && AUTH && PRIVATE && SHOW ? `/api/memes/pv/?n=${encodeURIComponent(PAGE_NAME)}`
                 : `/api/memes/?p=${encodeURIComponent(PN.slice(1))}`);
        },
        loadLikes(uuids) {
            if (AUTH && uuids.length) {
                axios.get(`/api/likes/m/?${uuids.slice(0, 20).map(uuid => `u=${uuid}`).join("&")}`)
                    .then(res => {
                        for (vote of res.data) {
                            const i = this.$children.findIndex(c => c.meme.uuid === vote["uuid"]);
                            this.$children[i].isLiked = vote["point"] === 1;
                            this.$children[i].isDisliked = vote["point"] === -1;
                        }
                    })
                    .catch(err => console.log(err));
            }
        }
    }
}) : undefined;

const SearchListComponent = {
    props: {
        result: {
            type: Object,
            required: true
        },
        searchUser: {
            type: Boolean,
            required: true
        }
    },
    data() {
        return {
            url: this.searchUser ? `/user/${this.result.username}` : `/page/${this.result.name}`,
            description: this.searchUser ? this.result.bio : this.result.description
        }
    },
    computed: {
        getDescription() {
            return this.description.replace(/\r\n/g, "  ")
        },
        getBottomText() {
            return this.searchUser ? `${this.result.meme_count} meme${this.result.meme_count === 1 ? "" : "s"}`
                                   : `${this.result.num_subscribers} subscriber${this.result.num_subscribers === 1 ? "" : "s"}`
        }
    },
    template: (
        `<li class="media my-4">
            <a class="mr-3" :href="url">
                <img v-if="result.dp_url" class="media-img rounded-circle" :src="result.dp_url" height="40" width="40">
                <i v-else :class="[searchUser ? 'fa-user' : 'fa-user-friends']" class="fas media-img"></i>
            </a>
            <div class="media-body">
                <h6 class="mt-0 mb-1"><a :href="url">{{ searchUser ? result.username : result.display_name || result.name }}</a></h6>
                <div v-if="description" class="bio"><span>{{ getDescription }}</span></div>
                <small class="text-muted">{{ getBottomText }}</small>
            </div>
        </li>`
    )
}

const SearchListInstance = document.querySelector("search-items") ? new Vue({
    el: "#search-list",
    components: {
        "search-items": SearchListComponent
    },
    data: {
        results: [],
        query: new URL(window.location.href).searchParams.get("q"),
        loading: false,
        next: "",
        scrollObserver: null,
        scrollRoot: null,
    },
    mounted() {
        this.loadSearches();
        createScrollObserver(this, this.loadSearches);
    },
    updated() {
        updateScrollObserver(this);
    },
    methods: {
        loadSearches() {
            if (this.next === null || !["@", "^"].includes(this.query[0])) return false;
            this.loading = true;

            axios.get(this.next || `/api/${this.query[0] === "@" ? "users" : "pages"}/?search=${encodeURIComponent(this.query.slice(1, 64))}`)
                .then(res => res.data)
                .then(response => {
                    if (response["results"].length) {
                        this.results.push(...response["results"]);
                        this.next = response["next"];
                    } else {
                        if (this.next === "" && !this.results.length) {
                            this.$el.innerHTML = `<div style="margin-top: 30px;text-align: center;">No results matching query.<br><br>Return <a href="/">home</a></div>`
                        }
                        if (this.scrollRoot) this.scrollObserver.unobserve(this.scrollRoot);
                        this.scrollObserver = this.scrollRoot = this.next = null;
                    }
                })
                .catch(err => console.log(err))
                .finally(() => this.loading = false);
        }
    }
}) : undefined;

function display_error(err) {
    window.innerWidth > 575.98 ? DangerAlertInstance.show(err.message) : alert(err);
}

const DangerAlertComponent = {
    props: {
        showing: {
            type: Boolean,
            required: true
        },
        message: {
            type: String,
            required: true
        }
    },
    template: (
        `<div v-show="showing" class="alert alert-danger" role="alert" id="d-alert">
            {{ message }}
            <button @click="$emit('hide')" type="button" class="close" aria-label="Close" style="font-weight: 500;">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>`
    )
}

const DangerAlertInstance = new Vue({
    el: "#danger-alert",
    components: {"danger-alert": DangerAlertComponent},
    data: {
        showing: false,
        message: ""
    },
    methods: {
        show(m) {
            this.showing = true;
            this.message = m;
            setTimeout(() => {this.hide()}, 2000);
        },
        hide() {
            this.showing = false
        }
    }
})

const sa = document.querySelector("#success-alert");
function display_success(m) {
    sa.textContent = m;
    sa.classList.remove("d-none");
    setTimeout(() => {sa.classList.add("d-none")}, 2000);
}

// const NotificationComponent = {
//     props: {
//         notif: {
//             type: Object,
//             required: true
//         }
//     },
//     data() {
//         return {

//         }
//     },
//     template: (
//         `<div class="notification row">
//             <div class="notif-left-column">
//                 <img v-if="notif.image" class="rounded-circle" src="{{ notif.image }}" height="50" width="50">
//                 <i v-else class="fas fa-user-circle" style="font-size: 50px;"></i>
//             </div>
//             <div class="notif-right-column">{{ notif.message }}</div>
//         </div>`
//     )
// }

// const NotificationDropdownComponent = {
//     components: {
//         "notification-items": NotificationComponent
//     },
//     data() {
//         return {
//             notifs: [],
//             seen: false
//         }
//     },
//     mounted() {
//         axios.get("/api/notifications")
//             .then(res => this.notifs.push(...res.data))
//             .catch(err => console.log(err));
//     },
//     template: (
//         `<div class="dropdown">
//             <a type="button" @click="view" :class="[seen ? 'mr-3' : 'mr-2']" class="nav-item nav-link text-light" id="notif-btn" data-toggle="dropdown"><i :class="[seen ? 'far' : 'fas']" class="fa-bell"></i> <small v-if="!seen" class="align-top"><small class="align-top"><span class="badge badge-pill badge-danger align-top">2</span></small></small></a>
//             <div class="dropdown-menu dropdown-menu-right">
//                 <h5 class="dropdown-header m-0">Notifications</h5>
//                 <div id="notifications" style="width: 100%;">
//                     <notification-items v-for="(notif, index) in notifs" :key="index" :notif="notif"></notification-items>
//                 </div>
//                 <div class="dropdown-divider"></div>
//                 <a class="dropdown-item user-dropdown" href="/notifications" style="text-align: center;font-size: small;">View all</a>
//             </div>
//         </div>`
//     ),
//     methods: {
//         view() {
//             if (!this.seen) {
//                 axios.patch("/api/notifications")
//                     .catch(err => console.log(err));
//             }
//             this.seen = true;
//         }
//     }
// }

// const NotificationInstance = new Vue({
//     el: "#notif-dropdown",
//     components: {"notification-dropdown": NotificationDropdownComponent}
// })
