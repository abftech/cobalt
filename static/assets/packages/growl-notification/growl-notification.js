!(function (t, i) {
    "object" == typeof exports && "object" == typeof module
        ? (module.exports = i())
        : "function" == typeof define && define.amd
        ? define("GrowlNotification", [], i)
        : "object" == typeof exports
        ? (exports.GrowlNotification = i())
        : (t.GrowlNotification = i());
})(window, function () {
    return (function (t) {
        var i = {};
        function o(n) {
            if (i[n]) return i[n].exports;
            var e = (i[n] = { i: n, l: !1, exports: {} });
            return t[n].call(e.exports, e, e.exports, o), (e.l = !0), e.exports;
        }
        return (
            (o.m = t),
            (o.c = i),
            (o.d = function (t, i, n) {
                o.o(t, i) || Object.defineProperty(t, i, { enumerable: !0, get: n });
            }),
            (o.r = function (t) {
                "undefined" != typeof Symbol && Symbol.toStringTag && Object.defineProperty(t, Symbol.toStringTag, { value: "Module" }), Object.defineProperty(t, "__esModule", { value: !0 });
            }),
            (o.t = function (t, i) {
                if ((1 & i && (t = o(t)), 8 & i)) return t;
                if (4 & i && "object" == typeof t && t && t.__esModule) return t;
                var n = Object.create(null);
                if ((o.r(n), Object.defineProperty(n, "default", { enumerable: !0, value: t }), 2 & i && "string" != typeof t))
                    for (var e in t)
                        o.d(
                            n,
                            e,
                            function (i) {
                                return t[i];
                            }.bind(null, e)
                        );
                return n;
            }),
            (o.n = function (t) {
                var i =
                    t && t.__esModule
                        ? function () {
                              return t.default;
                          }
                        : function () {
                              return t;
                          };
                return o.d(i, "a", i), i;
            }),
            (o.o = function (t, i) {
                return Object.prototype.hasOwnProperty.call(t, i);
            }),
            (o.p = ""),
            o((o.s = 7))
        );
    })([
        function (t, i, o) {
            "use strict";
            Object.defineProperty(i, "__esModule", { value: !0 }),
                (Number.isInteger =
                    Number.isInteger ||
                    function (t) {
                        return "number" == typeof t && isFinite(t) && Math.floor(t) === t;
                    });
            var n = (function () {
                function t(i, o) {
                    if (((this.nodes = []), (this.pseudoSelector = ""), (this.callbacks = {}), o || (o = document), "string" == typeof i))
                        if ("<" === i[0] && ">" === i[i.length - 1]) this.nodes = [t.createNode(i)];
                        else {
                            if (-1 !== i.search(/(:before|:after)$/gi)) {
                                var n = i.match(/(:before|:after)$/gi);
                                (i = i.split(n[0])[0]), (this.pseudoSelector = n[0]);
                            }
                            this.nodes = [].slice.call(o.querySelectorAll(i));
                        }
                    else i instanceof NodeList ? (this.nodes = i.length > 1 ? [].slice.call(i) : [i]) : (i instanceof HTMLDocument || i instanceof Window || i instanceof HTMLElement) && (this.nodes = [i]);
                }
                return (
                    (t.select = function (i, o) {
                        return new t(i, o);
                    }),
                    (t.create = function (i) {
                        return new t(t.createNode(i));
                    }),
                    (t.prototype.attr = function (t, i) {
                        return void 0 != i
                            ? (this.each(this.nodes, function (o) {
                                  o.setAttribute(t, i);
                              }),
                              this)
                            : this.getLastNode().getAttribute(t);
                    }),
                    (t.prototype.append = function (i) {
                        var o;
                        return (
                            (o = i instanceof t ? i.get() : i),
                            this.each(this.nodes, function (t) {
                                t.appendChild(o);
                            }),
                            this
                        );
                    }),
                    (t.prototype.parent = function () {
                        return new t(this.getLastNode().parentNode);
                    }),
                    (t.prototype.each = function (t, i) {
                        t instanceof Function && ((i = t), (t = this.nodes));
                        for (var o = 0; o < t.length; o++) i.call(this.nodes[o], this.nodes[o], o);
                        return this;
                    }),
                    (t.prototype.hasClass = function (t) {
                        return this.getLastNode().classList.contains(t);
                    }),
                    (t.prototype.addClass = function (t) {
                        if (t) {
                            var i = t.split(" ");
                            this.each(this.nodes, function (t) {
                                for (var o in i) t.classList.add(i[o]);
                            });
                        }
                        return this;
                    }),
                    (t.prototype.removeClass = function (t) {
                        var i = t.split(" ");
                        return (
                            this.each(this.nodes, function (t) {
                                for (var o in i) t.classList.remove(i[o]);
                            }),
                            this
                        );
                    }),
                    (t.prototype.find = function (i) {
                        return new t(i, this.getLastNode());
                    }),
                    (t.prototype.trigger = function (t, i) {
                        var o = new CustomEvent(t, { detail: i });
                        return (
                            this.each(this.nodes, function (t) {
                                t.dispatchEvent(o);
                            }),
                            this
                        );
                    }),
                    (t.prototype.text = function (t) {
                        return (
                            this.each(this.nodes, function (i) {
                                i.innerText = t;
                            }),
                            this
                        );
                    }),
                    (t.prototype.css = function (i, o) {
                        if (void 0 === o) {
                            var n = this.getLastNode(),
                                e = null;
                            if (((i = t.convertToJsProperty(i)), "function" != typeof n.getBoundingClientRect || this.pseudoSelector || (e = n.getBoundingClientRect()[i]), !e)) {
                                var s = getComputedStyle(n, this.pseudoSelector)[i];
                                s.search("px") && (e = parseInt(s, 10));
                            }
                            if (isNaN(e)) throw "Undefined css property: " + i;
                            return e;
                        }
                        return (
                            Number.isInteger(o) && (o += "px"),
                            this.nodes.length > 1
                                ? this.each(this.nodes, function (t) {
                                      t.style[i] = o;
                                  })
                                : (this.nodes[0].style[i] = o),
                            this
                        );
                    }),
                    (t.prototype.on = function (t, i) {
                        var o = this;
                        return (
                            this.each(this.nodes, function (n) {
                                var e = function (t) {
                                    i.call(n, t);
                                };
                                (o.callbacks[t] = e), n.addEventListener(t, e);
                            }),
                            this
                        );
                    }),
                    (t.prototype.off = function (t) {
                        var i = this.callbacks[t];
                        return (
                            this.each(this.nodes, function (o) {
                                o.removeEventListener(t, i, !1);
                            }),
                            this
                        );
                    }),
                    (t.prototype.val = function (t) {
                        return void 0 === t
                            ? this.getLastNode().value
                            : (this.each(this.nodes, function (i) {
                                  i.value = t;
                              }),
                              this);
                    }),
                    (t.prototype.is = function (t) {
                        return this.getLastNode().tagName.toLowerCase() === t;
                    }),
                    (t.prototype.get = function (t) {
                        return void 0 === t && (t = 0), this.nodes[t];
                    }),
                    (t.prototype.length = function () {
                        return this.nodes.length;
                    }),
                    (t.prototype.hide = function () {
                        return (
                            this.each(this.nodes, function (i) {
                                t.select(i).css("display", "none");
                            }),
                            this
                        );
                    }),
                    (t.prototype.show = function () {
                        return (
                            this.each(this.nodes, function (i) {
                                t.select(i).css("display", "");
                            }),
                            this
                        );
                    }),
                    (t.prototype.empty = function () {
                        return (
                            this.each(this.nodes, function (i) {
                                t.select(i).get().innerHTML = "";
                            }),
                            this
                        );
                    }),
                    (t.prototype.html = function (t) {
                        this.each(this.nodes, function (i) {
                            i.innerHTML = t;
                        });
                    }),
                    (t.prototype.remove = function () {
                        this.each(this.nodes, function (t) {
                            t.remove();
                        });
                    }),
                    (t.prototype.insertBefore = function (t) {
                        var i = this.resolveElement(t);
                        return (
                            this.each(this.nodes, function (t) {
                                t.parentNode.insertBefore(i, i.previousSibling);
                            }),
                            this
                        );
                    }),
                    (t.prototype.insertAfter = function (t) {
                        var i = this.resolveElement(t);
                        return (
                            this.each(this.nodes, function (t) {
                                t.parentNode.insertBefore(i, t.nextSibling);
                            }),
                            this
                        );
                    }),
                    (t.prototype.resolveElement = function (i) {
                        var o;
                        return t.isHtml(i) ? (o = t.createNode(i)) : i instanceof HTMLElement ? (o = i) : i instanceof t && (o = i.get()), o;
                    }),
                    (t.prototype.closest = function (i) {
                        return t.select(this.getLastNode().closest(i));
                    }),
                    (t.prototype.data = function (t) {
                        return this.attr("data-" + t);
                    }),
                    (t.prototype.width = function (t) {
                        return void 0 !== t ? (this.css("width", t), this) : this.getLastNode() === window ? parseInt(this.getLastNode().innerWidth, 10) : parseInt(this.css("width"), 10);
                    }),
                    (t.prototype.height = function (t) {
                        return void 0 !== t ? (this.css("height", t), this) : this.getLastNode() === window ? parseInt(this.getLastNode().innerHeight, 10) : parseInt(this.css("height"), 10);
                    }),
                    (t.prototype.position = function () {
                        return {
                            top: Number(this.getLastNode().getBoundingClientRect().top),
                            bottom: Number(this.getLastNode().getBoundingClientRect().bottom),
                            left: Number(this.getLastNode().getBoundingClientRect().left),
                            right: Number(this.getLastNode().getBoundingClientRect().right),
                        };
                    }),
                    (t.prototype.offset = function () {
                        return { top: Number(this.getLastNode().offsetTop), left: Number(this.getLastNode().offsetLeft) };
                    }),
                    (t.createNode = function (t) {
                        if ("<" === t[0] && ">" === t[t.length - 1]) {
                            var i = document.createElement("div");
                            return (i.innerHTML = t), i.firstChild;
                        }
                        return document.createElement(t);
                    }),
                    (t.isHtml = function (t) {
                        return "<" === t[0] && ">" === t[t.length - 1];
                    }),
                    (t.convertToJsProperty = function (t) {
                        return (t =
                            (t = (t = t.toLowerCase().replace("-", " ")).replace(/(^| )(\w)/g, function (t) {
                                return t.toUpperCase();
                            }))
                                .charAt(0)
                                .toLowerCase() + t.slice(1)).replace(" ", "");
                    }),
                    (t.prototype.getLastNode = function () {
                        return this.nodes[this.nodes.length - 1];
                    }),
                    t
                );
            })();
            i.default = n;
        },
        function (t, i, o) {
            "use strict";
            Object.defineProperty(i, "__esModule", { value: !0 });
            var n = o(0),
                e = (function () {
                    function t(t, i) {
                        (this.notification = t), (this.margin = i);
                    }
                    return (
                        (t.prototype.calculate = function () {
                            var i = this,
                                o = this.margin;
                            n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                n.default.select(t).css("top", o).css("right", i.margin), (o += n.default.select(t).height() + i.margin);
                            });
                        }),
                        (t.prototype.instances = function () {
                            var i = [];
                            return (
                                n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                    i.push(n.default.select(t));
                                }),
                                i
                            );
                        }),
                        (t.position = "top-right"),
                        t
                    );
                })();
            i.TopRightPosition = e;
        },
        function (t, i, o) {
            "use strict";
            Object.defineProperty(i, "__esModule", { value: !0 });
            var n = o(0),
                e = (function () {
                    function t(t, i) {
                        (this.notification = t), (this.margin = i);
                    }
                    return (
                        (t.prototype.calculate = function () {
                            var i = this,
                                o = this.margin;
                            n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                var e = n.default.select(t);
                                e.css("top", o).css("left", "calc(50% - " + Math.ceil(e.width() / 2) + "px)"), (o += e.height() + i.margin);
                            });
                        }),
                        (t.prototype.instances = function () {
                            var i = [];
                            return (
                                n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                    i.push(n.default.select(t));
                                }),
                                i
                            );
                        }),
                        (t.position = "top-center"),
                        t
                    );
                })();
            i.TopCenterPosition = e;
        },
        function (t, i, o) {
            "use strict";
            Object.defineProperty(i, "__esModule", { value: !0 });
            var n = o(0),
                e = (function () {
                    function t(t, i) {
                        (this.notification = t), (this.margin = i);
                    }
                    return (
                        (t.prototype.calculate = function () {
                            var i = this,
                                o = this.margin;
                            n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                var e = n.default.select(t);
                                e.css("bottom", o).css("right", i.margin), (o += e.height() + i.margin);
                            });
                        }),
                        (t.prototype.instances = function () {
                            var i = [];
                            return (
                                n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                    i.push(n.default.select(t));
                                }),
                                i
                            );
                        }),
                        (t.position = "bottom-right"),
                        t
                    );
                })();
            i.BottomRightPosition = e;
        },
        function (t, i, o) {
            "use strict";
            Object.defineProperty(i, "__esModule", { value: !0 });
            var n = o(0),
                e = (function () {
                    function t(t, i) {
                        (this.notification = t), (this.margin = i);
                    }
                    return (
                        (t.prototype.calculate = function () {
                            var i = this,
                                o = this.margin;
                            n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                var e = n.default.select(t);
                                e.css("top", o).css("left", i.margin), (o += e.height() + i.margin);
                            });
                        }),
                        (t.prototype.instances = function () {
                            var i = [];
                            return (
                                n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                    i.push(n.default.select(t));
                                }),
                                i
                            );
                        }),
                        (t.position = "top-left"),
                        t
                    );
                })();
            i.TopLeftPosition = e;
        },
        function (t, i, o) {
            "use strict";
            Object.defineProperty(i, "__esModule", { value: !0 });
            var n = o(0),
                e = (function () {
                    function t(t, i) {
                        (this.notification = t), (this.margin = i);
                    }
                    return (
                        (t.prototype.calculate = function () {
                            var i = this,
                                o = this.margin;
                            n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                var e = n.default.select(t);
                                e.css("bottom", o).css("left", "calc(50% - " + Math.ceil(e.width() / 2) + "px)"), (o += e.height() + i.margin);
                            });
                        }),
                        (t.prototype.instances = function () {
                            var i = [];
                            return (
                                n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                    i.push(n.default.select(t));
                                }),
                                i
                            );
                        }),
                        (t.position = "bottom-center"),
                        t
                    );
                })();
            i.BottomCenterPosition = e;
        },
        function (t, i, o) {
            "use strict";
            Object.defineProperty(i, "__esModule", { value: !0 });
            var n = o(0),
                e = (function () {
                    function t(t, i) {
                        (this.notification = t), (this.margin = i);
                    }
                    return (
                        (t.prototype.calculate = function () {
                            var i = this,
                                o = this.margin;
                            n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                var e = n.default.select(t);
                                e.css("bottom", o).css("left", i.margin), (o += e.height() + i.margin);
                            });
                        }),
                        (t.prototype.instances = function () {
                            var i = [];
                            return (
                                n.default.select(".growl-notification.position-" + t.position).each(function (t) {
                                    i.push(n.default.select(t));
                                }),
                                i
                            );
                        }),
                        (t.position = "bottom-left"),
                        t
                    );
                })();
            i.BottomLeftPosition = e;
        },
        function (t, i, o) {
            "use strict";
            o(10), o(15), o(17);
            var n = o(8),
                e = o(9),
                s = o(0),
                r = o(2),
                c = o(1),
                a = o(4),
                u = o(5),
                l = o(6),
                f = o(3),
                p = (function () {
                    function t(i) {
                        void 0 === i && (i = {}),
                            (this.options = e.all([t.defaultOptions, t.globalOptions, i])),
                            (this.options.animation.close && "none" != this.options.animation.close) || (this.options.animationDuration = 0),
                            (this.notification = s.default.create("div")),
                            (this.body = s.default.select("body")),
                            (this.template = t.template),
                            (this.position = n.PositionFactory.newInstance(this.options.position, this.notification, this.options.margin)),
                            t.instances.push(this);
                    }
                    return (
                        Object.defineProperty(t, "defaultOptions", {
                            get: function () {
                                return {
                                    margin: 20,
                                    type: "default",
                                    title: "",
                                    description: "",
                                    image: { visible: !1, customImage: "" },
                                    closeTimeout: 0,
                                    closeWith: ["click", "button"],
                                    animation: { open: "slide-in", close: "slide-out" },
                                    animationDuration: 0.2,
                                    position: "top-right",
                                    showBorder: !1,
                                    showButtons: !1,
                                    buttons: { action: { text: "Ok", callback: function () {} }, cancel: { text: "Cancel", callback: function () {} } },
                                    showProgress: !1,
                                };
                            },
                            enumerable: !0,
                            configurable: !0,
                        }),
                        Object.defineProperty(t, "template", {
                            get: function () {
                                return '<span class="growl-notification__close">\n                  <span class="growl-notification__close-icon"></span>\n                </span>\n                <div class="growl-notification__progress">\n                    <div class="growl-notification__progress-bar"></div>\n                </div>\n               <div class="growl-notification__body">\n                 {{ image }}\n                 <div class="growl-notification__content">\n                   <div class="growl-notification__title">{{ title }}</div>\n                   <div class="growl-notification__desc">{{ description }}</div>\n                 </div>\n                </div>\n                <div class="growl-notification__buttons">\n                    <span class="growl-notification__button growl-notification__button--action">Ok</span>\n                    <span class="growl-notification__button growl-notification__button--cancel">Cancel</span>\n                </div>';
                            },
                            enumerable: !0,
                            configurable: !0,
                        }),
                        (t.notify = function (i) {
                            void 0 === i && (i = {});
                            var o = new t(i).show(),
                                n = 0,
                                e = [];
                            return (
                                o.position.instances().forEach(function (i) {
                                    t.hasOverflow(o, n) && (e.push(i), (n += i.height() + o.options.margin));
                                }),
                                e.forEach(function (t) {
                                    t.remove();
                                }),
                                o.position.calculate(),
                                o
                            );
                        }),
                        (t.hasOverflow = function (t, i) {
                            void 0 === i && (i = 0);
                            var o = !1,
                                n = s.default.select(window).height();
                            return (
                                t.position instanceof r.TopCenterPosition || t.position instanceof c.TopRightPosition || t.position instanceof a.TopLeftPosition
                                    ? t.getContent().offset().top + t.getContent().height() + t.options.margin - i >= n && (o = !0)
                                    : (t.position instanceof u.BottomCenterPosition || t.position instanceof f.BottomRightPosition || t.position instanceof l.BottomLeftPosition) && t.getContent().offset().top + i <= 0 && (o = !0),
                                o
                            );
                        }),
                        (t.closeAll = function () {
                            (t.instances = []),
                                s.default.select(".growl-notification").each(function (t) {
                                    s.default.select(t).remove();
                                });
                        }),
                        (t.prototype.show = function () {
                            return this.addNotification(), this.initPosition(), this.bindEvents(), this;
                        }),
                        (t.prototype.close = function () {
                            var t = this;
                            this.notification
                                .removeClass("animation-" + this.options.animation.open)
                                .addClass("animation-" + this.options.animation.close)
                                .addClass("growl-notification--closed"),
                                setTimeout(function () {
                                    t.remove(), t.position.calculate();
                                }, 1e3 * this.options.animationDuration);
                        }),
                        (t.prototype.remove = function () {
                            var i = t.instances.indexOf(this);
                            return t.instances.splice(i, 1), this.notification.remove(), this;
                        }),
                        (t.prototype.getContent = function () {
                            return this.notification;
                        }),
                        (t.prototype.addNotification = function () {
                            var t = this.options,
                                i = this.template.replace("{{ title }}", t.title);
                            (i = i.replace("{{ description }}", t.description)),
                                (i = this.options.image.visible
                                    ? this.options.image.customImage
                                        ? i.replace("{{ image }}", '<div class="growl-notification__image growl-notification__image--custom"><img src="' + this.options.image.customImage + '" alt=""></div>')
                                        : i.replace("{{ image }}", '<div class="growl-notification__image"></div>')
                                    : i.replace("{{ image }}", "")),
                                this.notification
                                    .addClass("growl-notification")
                                    .addClass("growl-notification--" + t.type)
                                    .addClass("animation-" + t.animation.open)
                                    .addClass("position-" + t.position),
                                t.image && this.notification.addClass("growl-notification--image"),
                                this.notification.html(i),
                                t.title || this.notification.find(".growl-notification__title").remove(),
                                t.width && this.notification.width(t.width),
                                t.zIndex && this.notification.css("z-index", t.zIndex),
                                t.showProgress && t.closeTimeout > 0 && (this.notification.find(".growl-notification__progress").addClass("is-visible"), this.notification.addClass("has-progress")),
                                t.showButtons &&
                                    (this.notification.find(".growl-notification__buttons").addClass("is-visible"),
                                    this.notification.find(".growl-notification__button--action").text(t.buttons.action.text),
                                    this.notification.find(".growl-notification__button--cancel").text(t.buttons.cancel.text)),
                                this.body.append(this.notification),
                                t.showProgress && t.closeTimeout > 0 && this.calculateProgress();
                        }),
                        (t.prototype.initPosition = function () {
                            this.position.calculate();
                        }),
                        (t.prototype.calculateProgress = function () {
                            var t = this,
                                i = Math.ceil(Number(this.options.closeTimeout) / 100),
                                o = 1,
                                n = setInterval(function () {
                                    o >= 100 ? clearInterval(n) : (t.notification.find(".growl-notification__progress-bar").css("width", o + "%"), o++);
                                }, i);
                        }),
                        (t.prototype.bindEvents = function () {
                            var t = this;
                            if (this.options.closeWith.indexOf("click") > -1)
                                this.notification.addClass("growl-notification--close-on-click").on("click", function () {
                                    return t.close();
                                });
                            else if (this.options.closeWith.indexOf("button") > -1) {
                                this.notification.find(".growl-notification__close").on("click", function () {
                                    return t.close();
                                });
                            }
                            this.options.showButtons &&
                                (this.notification.find(".growl-notification__button--action").on("click", function (i) {
                                    t.options.buttons.action.callback.apply(t), t.close(), i.stopPropagation();
                                }),
                                this.notification.find(".growl-notification__button--cancel").on("click", function (i) {
                                    t.options.buttons.cancel.callback.apply(t), t.close(), i.stopPropagation();
                                }));
                            this.options.closeTimeout &&
                                this.options.closeTimeout > 0 &&
                                setTimeout(function () {
                                    return t.close();
                                }, this.options.closeTimeout);
                        }),
                        (t.setGlobalOptions = function (i) {
                            t.globalOptions = i;
                        }),
                        (t.globalOptions = {}),
                        (t.instances = []),
                        t
                    );
                })();
            t.exports = p;
        },
        function (t, i, o) {
            "use strict";
            Object.defineProperty(i, "__esModule", { value: !0 });
            var n = o(1),
                e = o(2),
                s = o(3),
                r = o(4),
                c = o(5),
                a = o(6),
                u = (function () {
                    function t() {}
                    return (
                        (t.newInstance = function (t, i, o) {
                            var u = null;
                            return (
                                t === n.TopRightPosition.position
                                    ? (u = n.TopRightPosition)
                                    : t === e.TopCenterPosition.position
                                    ? (u = e.TopCenterPosition)
                                    : t === s.BottomRightPosition.position
                                    ? (u = s.BottomRightPosition)
                                    : t === r.TopLeftPosition.position
                                    ? (u = r.TopLeftPosition)
                                    : t === c.BottomCenterPosition.position
                                    ? (u = c.BottomCenterPosition)
                                    : t === a.BottomLeftPosition.position && (u = a.BottomLeftPosition),
                                new u(i, o)
                            );
                        }),
                        t
                    );
                })();
            i.PositionFactory = u;
        },
        function (t, i, o) {
            t.exports = (function () {
                "use strict";
                var t = function (t) {
                        return (
                            (function (t) {
                                return !!t && "object" == typeof t;
                            })(t) &&
                            !(function (t) {
                                var o = Object.prototype.toString.call(t);
                                return (
                                    "[object RegExp]" === o ||
                                    "[object Date]" === o ||
                                    (function (t) {
                                        return t.$$typeof === i;
                                    })(t)
                                );
                            })(t)
                        );
                    },
                    i = "function" == typeof Symbol && Symbol.for ? Symbol.for("react.element") : 60103;
                function o(t, i) {
                    return !1 !== i.clone && i.isMergeableObject(t)
                        ? e(
                              (function (t) {
                                  return Array.isArray(t) ? [] : {};
                              })(t),
                              t,
                              i
                          )
                        : t;
                }
                function n(t, i, n) {
                    return t.concat(i).map(function (t) {
                        return o(t, n);
                    });
                }
                function e(i, s, r) {
                    ((r = r || {}).arrayMerge = r.arrayMerge || n), (r.isMergeableObject = r.isMergeableObject || t);
                    var c = Array.isArray(s),
                        a = Array.isArray(i),
                        u = c === a;
                    return u
                        ? c
                            ? r.arrayMerge(i, s, r)
                            : (function (t, i, n) {
                                  var s = {};
                                  return (
                                      n.isMergeableObject(t) &&
                                          Object.keys(t).forEach(function (i) {
                                              s[i] = o(t[i], n);
                                          }),
                                      Object.keys(i).forEach(function (r) {
                                          n.isMergeableObject(i[r]) && t[r] ? (s[r] = e(t[r], i[r], n)) : (s[r] = o(i[r], n));
                                      }),
                                      s
                                  );
                              })(i, s, r)
                        : o(s, r);
                }
                return (
                    (e.all = function (t, i) {
                        if (!Array.isArray(t)) throw new Error("first argument should be an array");
                        return t.reduce(function (t, o) {
                            return e(t, o, i);
                        }, {});
                    }),
                    e
                );
            })();
        },
        function (t, i) {},
        ,
        ,
        ,
        ,
        function (t, i) {},
        ,
        function (t, i) {},
    ]);
});
