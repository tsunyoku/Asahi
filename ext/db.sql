--
-- PostgreSQL database dump
--

-- Dumped from database version 10.16 (Ubuntu 10.16-0ubuntu0.18.04.1)
-- Dumped by pg_dump version 10.16 (Ubuntu 10.16-0ubuntu0.18.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: channels; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE TABLE public.channels (
    id integer NOT NULL,
    name text NOT NULL,
    descr text NOT NULL,
    auto integer DEFAULT 1 NOT NULL,
    perm integer DEFAULT 1 NOT NULL
);

CREATE TABLE public.user_hashes(
    uid integer NOT NULL,
    mac_address text NOT NULL,
    uninstall_id text NOT NULL,
    disk_serial text NOT NULL,
    ip text NOT NULL,
    occurrences integer DEFAULT 1 NOT NULL,
    PRIMARY KEY (uid, mac_address, uninstall_id, disk_serial, ip)
);

CREATE TABLE public.requests(
    id SERIAL,
    requester text NOT NULL,
    map integer NOT NULL,
    status integer NOT NULL,
    mode integer DEFAULT 0 NOT NULL,
    UNIQUE (map)
);

ALTER TABLE public.channels OWNER TO tsunyoku;

--
-- Name: channels_id_seq; Type: SEQUENCE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.channels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.channels_id_seq OWNER TO tsunyoku;

--
-- Name: channels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tsunyoku
--

ALTER SEQUENCE public.channels_id_seq OWNED BY public.channels.id;


--
-- Name: friends; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE TABLE public.friends (
    id integer NOT NULL,
    user1 integer NOT NULL,
    user2 integer NOT NULL
);


ALTER TABLE public.friends OWNER TO tsunyoku;

--
-- Name: friends_id_seq; Type: SEQUENCE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.friends_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.friends_id_seq OWNER TO tsunyoku;

--
-- Name: friends_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tsunyoku
--

ALTER SEQUENCE public.friends_id_seq OWNED BY public.friends.id;


--
-- Name: stats; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE TABLE public.stats (
    id integer NOT NULL,
    rscore_std integer DEFAULT 0 NOT NULL,
    acc_std real DEFAULT 0.00 NOT NULL,
    pc_std integer DEFAULT 0 NOT NULL,
    tscore_std integer DEFAULT 0 NOT NULL,
    pp_std integer DEFAULT 0 NOT NULL,
    rscore_mania integer DEFAULT 0 NOT NULL,
    acc_mania real DEFAULT 0.00 NOT NULL,
    pc_mania integer DEFAULT 0 NOT NULL,
    tscore_mania integer DEFAULT 0 NOT NULL,
    rscore_catch integer DEFAULT 0 NOT NULL,
    acc_catch real DEFAULT 0.00 NOT NULL,
    pc_catch integer DEFAULT 0 NOT NULL,
    tscore_catch integer DEFAULT 0 NOT NULL,
    rscore_taiko integer DEFAULT 0 NOT NULL,
    acc_taiko real DEFAULT 0.00 NOT NULL,
    pc_taiko integer DEFAULT 0 NOT NULL,
    tscore_taiko integer DEFAULT 0 NOT NULL,
    pp_taiko integer DEFAULT 0 NOT NULL,
    pp_catch integer DEFAULT 0 NOT NULL,
    pp_mania integer DEFAULT 0 NOT NULL,
    rscore_catch_rx integer DEFAULT 0 NOT NULL,
    acc_catch_rx real DEFAULT 0.00 NOT NULL,
    pc_catch_rx integer DEFAULT 0 NOT NULL,
    tscore_catch_rx integer DEFAULT 0 NOT NULL,
    rscore_taiko_rx integer DEFAULT 0 NOT NULL,
    acc_taiko_rx real DEFAULT 0.00 NOT NULL,
    pc_taiko_rx integer DEFAULT 0 NOT NULL,
    tscore_taiko_rx integer DEFAULT 0 NOT NULL,
    rscore_std_ap integer DEFAULT 0 NOT NULL,
    acc_std_ap real DEFAULT 0.00 NOT NULL,
    pc_std_ap integer DEFAULT 0 NOT NULL,
    tscore_std_ap integer DEFAULT 0 NOT NULL,
    rscore_std_rx integer DEFAULT 0 NOT NULL,
    acc_std_rx real DEFAULT 0.00 NOT NULL,
    pc_std_rx integer DEFAULT 0 NOT NULL,
    tscore_std_rx integer DEFAULT 0 NOT NULL,
    pp_std_rx integer DEFAULT 0 NOT NULL,
    pp_std_ap integer DEFAULT 0 NOT NULL,
    pp_taiko_rx integer DEFAULT 0 NOT NULL,
    pp_catch_rx integer DEFAULT 0 NOT NULL,
    mc_std integer DEFAULT 0 NOT NULL,
    mc_std_rx integer DEFAULT 0 NOT NULL,
    mc_std_ap integer DEFAULT 0 NOT NULL,
    mc_taiko integer DEFAULT 0 NOT NULL,
    mc_taiko_rx integer DEFAULT 0 NOT NULL,
    mc_catch integer DEFAULT 0 NOT NULL,
    mc_catch_rx integer DEFAULT 0 NOT NULL,
    mc_mania integer DEFAULT 0 NOT NULL,
    pt_std integer DEFAULT 0 NOT NULL,
    pt_std_rx integer DEFAULT 0 NOT NULL,
    pt_std_ap integer DEFAULT 0 NOT NULL,
    pt_taiko integer DEFAULT 0 NOT NULL,
    pt_taiko_rx integer DEFAULT 0 NOT NULL,
    pt_catch integer DEFAULT 0 NOT NULL,
    pt_catch_rx integer DEFAULT 0 NOT NULL,
    pt_mania integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.stats OWNER TO tsunyoku;

--
-- Name: stats_id_seq; Type: SEQUENCE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.stats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stats_id_seq OWNER TO tsunyoku;

--
-- Name: stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tsunyoku
--

ALTER SEQUENCE public.stats_id_seq OWNED BY public.stats.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying(16) NOT NULL,
    email character varying(254) DEFAULT ''::character varying NOT NULL,
    pw text NOT NULL,
    country character varying(2) DEFAULT 'xx'::character varying NOT NULL,
    priv integer DEFAULT 1 NOT NULL,
    safe_name character varying(16) NOT NULL,
    clan integer DEFAULT 0 NOT NULL,
    freeze_timer bigint DEFAULT 0 NOT NULL,
    registered_at bigint DEFAULT 0 NOT NULL,
    silence_end bigint DEFAULT 0 NOT NULL,
    donor_end bigint DEFAULT 0 NOT NULL
);


ALTER TABLE public.users OWNER TO tsunyoku;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO tsunyoku;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tsunyoku
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: channels id; Type: DEFAULT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.channels ALTER COLUMN id SET DEFAULT nextval('public.channels_id_seq'::regclass);


--
-- Name: friends id; Type: DEFAULT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.friends ALTER COLUMN id SET DEFAULT nextval('public.friends_id_seq'::regclass);


--
-- Name: stats id; Type: DEFAULT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.stats ALTER COLUMN id SET DEFAULT nextval('public.stats_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: channels; Type: TABLE DATA; Schema: public; Owner: tsunyoku
--

COPY public.channels (id, name, descr, auto, perm) FROM stdin;
1	#osu	So true!!!	1	1
2	#asahi	owo	0	1
\.


--
-- Data for Name: stats; Type: TABLE DATA; Schema: public; Owner: tsunyoku
--

COPY public.stats (id, rscore_std, acc_std, pc_std, tscore_std, pp_std, rscore_mania, acc_mania, pc_mania, tscore_mania, rscore_catch, acc_catch, pc_catch, tscore_catch, rscore_taiko, acc_taiko, pc_taiko, tscore_taiko, pp_taiko, pp_catch, pp_mania, rscore_catch_rx, acc_catch_rx, pc_catch_rx, tscore_catch_rx, rscore_taiko_rx, acc_taiko_rx, pc_taiko_rx, tscore_taiko_rx, rscore_std_ap, acc_std_ap, pc_std_ap, tscore_std_ap, rscore_std_rx, acc_std_rx, pc_std_rx, tscore_std_rx, pp_std_rx, pp_std_ap, pp_taiko_rx, pp_catch_rx) FROM stdin;
1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: tsunyoku
--

COPY public.users (id, name, email, pw, country, priv, safe_name) FROM stdin;
1	Asahi		epic_bcrypt_goes_here	gb	1	asahi
\.


--
-- Name: channels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tsunyoku
--

SELECT pg_catalog.setval('public.channels_id_seq', 1, true);


--
-- Name: friends_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tsunyoku
--

SELECT pg_catalog.setval('public.friends_id_seq', 1, true);


--
-- Name: stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tsunyoku
--

SELECT pg_catalog.setval('public.stats_id_seq', 2, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tsunyoku
--

SELECT pg_catalog.setval('public.users_id_seq', 2, true);

--
-- Name: maps; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE TABLE public.maps (
    id integer NOT NULL,
    sid integer NOT NULL,
    md5 text NOT NULL,
    bpm double precision NOT NULL,
    cs double precision NOT NULL,
    ar double precision NOT NULL,
    od double precision NOT NULL,
    hp double precision NOT NULL,
    sr double precision NOT NULL,
    mode integer NOT NULL,
    artist text NOT NULL,
    title text NOT NULL,
    diff text NOT NULL,
    mapper text NOT NULL,
    status integer NOT NULL,
    frozen integer NOT NULL,
    update bigint NOT NULL,
    nc bigint DEFAULT 0 NOT NULL,
    plays integer DEFAULT 0 NOT NULL,
    passes integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.maps OWNER TO tsunyoku;

--
-- Name: maps maps_md5_key; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.maps
    ADD CONSTRAINT maps_md5_key UNIQUE (md5);

--
-- Name: scores; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.scores_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.scores_id_seq OWNER TO tsunyoku;

CREATE TABLE public.scores (
    id integer DEFAULT nextval('public.scores_id_seq'::regclass) NOT NULL,
    md5 text NOT NULL,
    score bigint NOT NULL,
    acc double precision NOT NULL,
    pp double precision NOT NULL,
    combo integer NOT NULL,
    mods integer NOT NULL,
    n300 integer NOT NULL,
    geki integer NOT NULL,
    n100 integer NOT NULL,
    katu integer NOT NULL,
    n50 integer NOT NULL,
    miss integer NOT NULL,
    grade text DEFAULT 'F'::text NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    mode integer NOT NULL,
    "time" bigint NOT NULL,
    uid integer NOT NULL,
    readable_mods text NOT NULL,
    fc integer NOT NULL,
    osuver double precision DEFAULT 0 NOT NULL
);


ALTER TABLE public.scores OWNER TO tsunyoku;

--
-- Name: scores scores_pkey; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_pkey PRIMARY KEY (id);

--
-- Name: scores_rx; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.scores_rx_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.scores_rx_id_seq OWNER TO tsunyoku;

CREATE TABLE public.scores_rx (
    id integer DEFAULT nextval('public.scores_rx_id_seq'::regclass) NOT NULL,
    md5 text NOT NULL,
    score bigint NOT NULL,
    acc double precision NOT NULL,
    pp double precision NOT NULL,
    combo integer NOT NULL,
    mods integer NOT NULL,
    n300 integer NOT NULL,
    geki integer NOT NULL,
    n100 integer NOT NULL,
    katu integer NOT NULL,
    n50 integer NOT NULL,
    miss integer NOT NULL,
    grade text DEFAULT 'F'::text NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    mode integer NOT NULL,
    "time" bigint NOT NULL,
    uid integer NOT NULL,
    readable_mods text NOT NULL,
    fc integer NOT NULL,
    osuver double precision DEFAULT 0 NOT NULL
);


ALTER TABLE public.scores_rx OWNER TO tsunyoku;

--
-- Name: scores_rx scores_rx_pkey; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.scores_rx
    ADD CONSTRAINT scores_rx_pkey PRIMARY KEY (id);

--
-- Name: scores_ap; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.scores_ap_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.scores_ap_id_seq OWNER TO tsunyoku;

CREATE TABLE public.scores_ap (
    id integer DEFAULT nextval('public.scores_ap_id_seq'::regclass) NOT NULL,
    md5 text NOT NULL,
    score bigint NOT NULL,
    acc double precision NOT NULL,
    pp double precision NOT NULL,
    combo integer NOT NULL,
    mods integer NOT NULL,
    n300 integer NOT NULL,
    geki integer NOT NULL,
    n100 integer NOT NULL,
    katu integer NOT NULL,
    n50 integer NOT NULL,
    miss integer NOT NULL,
    grade text DEFAULT 'F'::text NOT NULL,
    status integer DEFAULT 0 NOT NULL,
    mode integer NOT NULL,
    "time" bigint NOT NULL,
    uid integer NOT NULL,
    readable_mods text NOT NULL,
    fc integer NOT NULL,
    osuver double precision DEFAULT 0 NOT NULL
);


ALTER TABLE public.scores_ap OWNER TO tsunyoku;

--
-- Name: scores_ap scores_ap_pkey; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.scores_ap
    ADD CONSTRAINT scores_ap_pkey PRIMARY KEY (id);

--
-- Name: clans; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.clans_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.clans_id_seq OWNER TO tsunyoku;

CREATE TABLE public.clans (
    id integer DEFAULT nextval('public.clans_id_seq'::regclass) NOT NULL,
    name text NOT NULL,
    tag text NOT NULL,
    owner integer NOT NULL,
    score integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.clans OWNER TO tsunyoku;

--
-- Name: clans clans_pkey; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.clans
    ADD CONSTRAINT clans_pkey PRIMARY KEY (id);

--
-- Name: punishments; Type: TABLE; Schema: public; Owner: tsunyoku
--

CREATE TABLE public.punishments (
                                    id integer NOT NULL,
                                    type text NOT NULL,
                                    reason text NOT NULL,
                                    target integer NOT NULL,
                                    `from` integer NOT NULL,
                                    time integer not NULL
);


ALTER TABLE public.punishments OWNER TO tsunyoku;

--
-- Name: punishments_id_seq; Type: SEQUENCE; Schema: public; Owner: tsunyoku
--

CREATE SEQUENCE public.punishments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.punishments_id_seq OWNER TO tsunyoku;

--
-- Name: punishments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tsunyoku
--

ALTER SEQUENCE public.punishments_id_seq OWNED BY public.punishments.id;

ALTER TABLE ONLY public.punishments ALTER COLUMN id SET DEFAULT nextval('public.punishments_id_seq'::regclass);

CREATE TABLE public.achievements (
                                    id integer NOT NULL,
                                    image text NOT NULL,
                                    name text NOT NULL,
                                    descr text NOT NULL,
                                    cond text NOT NULL,
                                    custom integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.achievements OWNER TO tsunyoku;

CREATE SEQUENCE public.achievements_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.achievements_id_seq OWNER TO tsunyoku;


ALTER SEQUENCE public.achievements_id_seq OWNED BY public.achievements.id;

ALTER TABLE ONLY public.achievements ALTER COLUMN id SET DEFAULT nextval('public.achievements_id_seq'::regclass);

insert into public.achievements (id, image, name, descr, cond) values (1, 'osu-skill-pass-1', 'Rising Star', 'Can''t go forward without the first steps.', '(s.mods & 1 == 0) and 1 <= s.sr < 2 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (2, 'osu-skill-pass-2', 'Constellation Prize', 'Definitely not a consolation prize. Now things start getting hard!', '(s.mods & 1 == 0) and 2 <= s.sr < 3 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (3, 'osu-skill-pass-3', 'Building Confidence', 'Oh, you''ve SO got this.', '(s.mods & 1 == 0) and 3 <= s.sr < 4 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (4, 'osu-skill-pass-4', 'Insanity Approaches', 'You''re not twitching, you''re just ready.', '(s.mods & 1 == 0) and 4 <= s.sr < 5 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (5, 'osu-skill-pass-5', 'These Clarion Skies', 'Everything seems so clear now.', '(s.mods & 1 == 0) and 5 <= s.sr < 6 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (6, 'osu-skill-pass-6', 'Above and Beyond', 'A cut above the rest.', '(s.mods & 1 == 0) and 6 <= s.sr < 7 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (7, 'osu-skill-pass-7', 'Supremacy', 'All marvel before your prowess.', '(s.mods & 1 == 0) and 7 <= s.sr < 8 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (8, 'osu-skill-pass-8', 'Absolution', 'My god, you''re full of stars!', '(s.mods & 1 == 0) and 8 <= s.sr < 9 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (9, 'osu-skill-pass-9', 'Event Horizon', 'No force dares to pull you under.', '(s.mods & 1 == 0) and 9 <= s.sr < 10 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (10, 'osu-skill-pass-10', 'Phantasm', 'Fevered is your passion, extraordinary is your skill.', '(s.mods & 1 == 0) and 10 <= s.sr < 11 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (11, 'osu-skill-fc-1', 'Totality', 'All the notes. Every single one.', 's.fc and 1 <= s.sr < 2 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (12, 'osu-skill-fc-2', 'Business As Usual', 'Two to go, please.', 's.fc and 2 <= s.sr < 3 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (13, 'osu-skill-fc-3', 'Building Steam', 'Hey, this isn''t so bad.', 's.fc and 3 <= s.sr < 4 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (14, 'osu-skill-fc-4', 'Moving Forward', 'Bet you feel good about that.', 's.fc and 4 <= s.sr < 5 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (15, 'osu-skill-fc-5', 'Paradigm Shift', 'Surprisingly difficult.', 's.fc and 5 <= s.sr < 6 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (16, 'osu-skill-fc-6', 'Anguish Quelled', 'Don''t choke.', 's.fc and 6 <= s.sr < 7 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (17, 'osu-skill-fc-7', 'Never Give Up', 'Excellence is its own reward.', 's.fc and 7 <= s.sr < 8 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (18, 'osu-skill-fc-8', 'Aberration', 'They said it couldn''t be done. They were wrong.', 's.fc and 8 <= s.sr < 9 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (19, 'osu-skill-fc-9', 'Chosen', 'Reign among the Prometheans, where you belong.', 's.fc and 9 <= s.sr < 10 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (20, 'osu-skill-fc-10', 'Unfathomable', 'You have no equal.', 's.fc and 10 <= s.sr < 11 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (21, 'osu-combo-500', '500 Combo', '500 big ones! You''re moving up in the world!', '500 <= s.combo < 750 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (22, 'osu-combo-750', '750 Combo', '750 notes back to back? Woah.', '750 <= s.combo < 1000 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (23, 'osu-combo-1000', '1000 Combo', 'A thousand reasons why you rock at this game.', '1000 <= s.combo < 2000 and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (24, 'osu-combo-2000', '2000 Combo', 'Nothing can stop you now.', '2000 <= s.combo and s.mode.as_vn == 0');
insert into public.achievements (id, image, name, descr, cond) values (25, 'taiko-skill-pass-1', 'My First Don', 'Marching to the beat of your own drum. Literally.', '(s.mods & 1 == 0) and 1 <= s.sr < 2 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (26, 'taiko-skill-pass-2', 'Katsu Katsu Katsu', 'Hora! Izuko!', '(s.mods & 1 == 0) and 2 <= s.sr < 3 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (27, 'taiko-skill-pass-3', 'Not Even Trying', 'Muzukashii? Not even.', '(s.mods & 1 == 0) and 3 <= s.sr < 4 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (28, 'taiko-skill-pass-4', 'Face Your Demons', 'The first trials are now behind you, but are you a match for the Oni?', '(s.mods & 1 == 0) and 4 <= s.sr < 5 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (29, 'taiko-skill-pass-5', 'The Demon Within', 'No rest for the wicked.', '(s.mods & 1 == 0) and 5 <= s.sr < 6 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (30, 'taiko-skill-pass-6', 'Drumbreaker', 'Too strong.', '(s.mods & 1 == 0) and 6 <= s.sr < 7 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (31, 'taiko-skill-pass-7', 'The Godfather', 'You are the Don of Dons.', '(s.mods & 1 == 0) and 7 <= s.sr < 8 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (32, 'taiko-skill-pass-8', 'Rhythm Incarnate', 'Feel the beat. Become the beat.', '(s.mods & 1 == 0) and 8 <= s.sr < 9 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (33, 'taiko-skill-fc-1', 'Keeping Time', 'Don, then katsu. Don, then katsu..', 's.fc and 1 <= s.sr < 2 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (34, 'taiko-skill-fc-2', 'To Your Own Beat', 'Straight and steady.', 's.fc and 2 <= s.sr < 3 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (35, 'taiko-skill-fc-3', 'Big Drums', 'Bigger ss to match.', 's.fc and 3 <= s.sr < 4 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (36, 'taiko-skill-fc-4', 'Adversity Overcome', 'Difficult? Not for you.', 's.fc and 4 <= s.sr < 5 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (37, 'taiko-skill-fc-5', 'Demonslayer', 'An Oni felled forevermore.', 's.fc and 5 <= s.sr < 6 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (38, 'taiko-skill-fc-6', 'Rhythm''s Call', 'Heralding true skill.', 's.fc and 6 <= s.sr < 7 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (39, 'taiko-skill-fc-7', 'Time Everlasting', 'Not a single beat escapes you.', 's.fc and 7 <= s.sr < 8 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (40, 'taiko-skill-fc-8', 'The Drummer''s Throne', 'Percussive brilliance befitting royalty alone.', 's.fc and 8 <= s.sr < 9 and s.mode.as_vn == 1');
insert into public.achievements (id, image, name, descr, cond) values (41, 'fruits-skill-pass-1', 'A Slice Of Life', 'Hey, this fruit catching business isn''t bad.', '(s.mods & 1 == 0) and 1 <= s.sr < 2 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (42, 'fruits-skill-pass-2', 'Dashing Ever Forward', 'Fast is how you do it.', '(s.mods & 1 == 0) and 2 <= s.sr < 3 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (43, 'fruits-skill-pass-3', 'Zesty Disposition', 'No scurvy for you, not with that much fruit.', '(s.mods & 1 == 0) and 3 <= s.sr < 4 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (44, 'fruits-skill-pass-4', 'Hyperdash ON!', 'Time and distance is no obstacle to you.', '(s.mods & 1 == 0) and 4 <= s.sr < 5 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (45, 'fruits-skill-pass-5', 'It''s Raining Fruit', 'And you can catch them all.', '(s.mods & 1 == 0) and 5 <= s.sr < 6 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (46, 'fruits-skill-pass-6', 'Fruit Ninja', 'Legendary techniques.', '(s.mods & 1 == 0) and 6 <= s.sr < 7 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (47, 'fruits-skill-pass-7', 'Dreamcatcher', 'No fruit, only dreams now.', '(s.mods & 1 == 0) and 7 <= s.sr < 8 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (48, 'fruits-skill-pass-8', 'Lord of the Catch', 'Your kingdom kneels before you.', '(s.mods & 1 == 0) and 8 <= s.sr < 9 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (49, 'fruits-skill-fc-1', 'Sweet And Sour', 'Apples and oranges, literally.', 's.fc and 1 <= s.sr < 2 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (50, 'fruits-skill-fc-2', 'Reaching The Core', 'The seeds of future success.', 's.fc and 2 <= s.sr < 3 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (51, 'fruits-skill-fc-3', 'Clean Platter', 'Clean only of failure. It is completely full, otherwise.', 's.fc and 3 <= s.sr < 4 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (52, 'fruits-skill-fc-4', 'Between The Rain', 'No umbrella needed.', 's.fc and 4 <= s.sr < 5 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (53, 'fruits-skill-fc-5', 'Addicted', 'That was an overdose?', 's.fc and 5 <= s.sr < 6 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (54, 'fruits-skill-fc-6', 'Quickening', 'A dash above normal limits.', 's.fc and 6 <= s.sr < 7 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (55, 'fruits-skill-fc-7', 'Supersonic', 'Faster than is reasonably necessary.', 's.fc and 7 <= s.sr < 8 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (56, 'fruits-skill-fc-8', 'Dashing Scarlet', 'Speed beyond mortal reckoning.', 's.fc and 8 <= s.sr < 9 and s.mode.as_vn == 2');
insert into public.achievements (id, image, name, descr, cond) values (57, 'mania-skill-pass-1', 'First Steps', 'It isn''t 9-to-5, but 1-to-9. Keys, that is.', '(s.mods & 1 == 0) and 1 <= s.sr < 2 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (58, 'mania-skill-pass-2', 'No Normal Player', 'Not anymore, at least.', '(s.mods & 1 == 0) and 2 <= s.sr < 3 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (59, 'mania-skill-pass-3', 'Impulse Drive', 'Not quite hyperspeed, but getting close.', '(s.mods & 1 == 0) and 3 <= s.sr < 4 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (60, 'mania-skill-pass-4', 'Hyperspeed', 'Woah.', '(s.mods & 1 == 0) and 4 <= s.sr < 5 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (61, 'mania-skill-pass-5', 'Ever Onwards', 'Another challenge is just around the corner.', '(s.mods & 1 == 0) and 5 <= s.sr < 6 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (62, 'mania-skill-pass-6', 'Another Surpassed', 'Is there no limit to your skills?', '(s.mods & 1 == 0) and 6 <= s.sr < 7 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (63, 'mania-skill-pass-7', 'Extra Credit', 'See me after class.', '(s.mods & 1 == 0) and 7 <= s.sr < 8 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (64, 'mania-skill-pass-8', 'Maniac', 'There''s just no stopping you.', '(s.mods & 1 == 0) and 8 <= s.sr < 9 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (65, 'mania-skill-fc-1', 'Keystruck', 'The beginning of a new story', 's.fc and 1 <= s.sr < 2 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (66, 'mania-skill-fc-2', 'Keying In', 'Finding your groove.', 's.fc and 2 <= s.sr < 3 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (67, 'mania-skill-fc-3', 'Hyperflow', 'You can *feel* the rhythm.', 's.fc and 3 <= s.sr < 4 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (68, 'mania-skill-fc-4', 'Breakthrough', 'Many skills mastered, rolled into one.', 's.fc and 4 <= s.sr < 5 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (69, 'mania-skill-fc-5', 'Everything Extra', 'Giving your all is giving everything you have.', 's.fc and 5 <= s.sr < 6 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (70, 'mania-skill-fc-6', 'Level Breaker', 'Finesse beyond reason', 's.fc and 6 <= s.sr < 7 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (71, 'mania-skill-fc-7', 'Step Up', 'A precipice rarely seen.', 's.fc and 7 <= s.sr < 8 and s.mode.as_vn == 3');
insert into public.achievements (id, image, name, descr, cond) values (72, 'mania-skill-fc-8', 'Behind The Veil', 'Supernatural!', 's.fc and 8 <= s.sr < 9 and s.mode.as_vn == 3');


--
-- PostgreSQL database dump complete
--

