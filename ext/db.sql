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
    mc_mania integer DEFAULT 0 NOT NULL
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
    clan integer DEFAULT 0 NOT NULL
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
    nc bigint DEFAULT 0 NOT NULL
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
    fc integer NOT NULL
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
    fc integer NOT NULL
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
    fc integer NOT NULL
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
-- PostgreSQL database dump complete
--

