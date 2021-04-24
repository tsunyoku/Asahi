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
    rank_std integer DEFAULT 0 NOT NULL,
    pp_std integer DEFAULT 0 NOT NULL,
    rscore_mania integer DEFAULT 0 NOT NULL,
    acc_mania real DEFAULT 0.00 NOT NULL,
    pc_mania integer DEFAULT 0 NOT NULL,
    tscore_mania integer DEFAULT 0 NOT NULL,
    rank_mania integer DEFAULT 0 NOT NULL,
    rscore_catch integer DEFAULT 0 NOT NULL,
    acc_catch real DEFAULT 0.00 NOT NULL,
    pc_catch integer DEFAULT 0 NOT NULL,
    tscore_catch integer DEFAULT 0 NOT NULL,
    rank_catch integer DEFAULT 0 NOT NULL,
    rscore_taiko integer DEFAULT 0 NOT NULL,
    acc_taiko real DEFAULT 0.00 NOT NULL,
    pc_taiko integer DEFAULT 0 NOT NULL,
    tscore_taiko integer DEFAULT 0 NOT NULL,
    rank_taiko integer DEFAULT 0 NOT NULL,
    pp_taiko integer DEFAULT 0 NOT NULL,
    pp_catch integer DEFAULT 0 NOT NULL,
    pp_mania integer DEFAULT 0 NOT NULL,
    rscore_catch_rx integer DEFAULT 0 NOT NULL,
    acc_catch_rx real DEFAULT 0.00 NOT NULL,
    pc_catch_rx integer DEFAULT 0 NOT NULL,
    tscore_catch_rx integer DEFAULT 0 NOT NULL,
    rank_catch_rx integer DEFAULT 0 NOT NULL,
    rscore_taiko_rx integer DEFAULT 0 NOT NULL,
    acc_taiko_rx real DEFAULT 0.00 NOT NULL,
    pc_taiko_rx integer DEFAULT 0 NOT NULL,
    tscore_taiko_rx integer DEFAULT 0 NOT NULL,
    rank_taiko_rx integer DEFAULT 0 NOT NULL,
    rscore_std_ap integer DEFAULT 0 NOT NULL,
    acc_std_ap real DEFAULT 0.00 NOT NULL,
    pc_std_ap integer DEFAULT 0 NOT NULL,
    tscore_std_ap integer DEFAULT 0 NOT NULL,
    rank_std_ap integer DEFAULT 0 NOT NULL,
    rscore_std_rx integer DEFAULT 0 NOT NULL,
    acc_std_rx real DEFAULT 0.00 NOT NULL,
    pc_std_rx integer DEFAULT 0 NOT NULL,
    tscore_std_rx integer DEFAULT 0 NOT NULL,
    rank_std_rx integer DEFAULT 0 NOT NULL,
    pp_std_rx integer DEFAULT 0 NOT NULL,
    pp_std_ap integer DEFAULT 0 NOT NULL,
    pp_taiko_rx integer DEFAULT 0 NOT NULL,
    pp_catch_rx integer DEFAULT 0 NOT NULL
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
    priv integer DEFAULT 1 NOT NULL
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

COPY public.stats (id, rscore_std, acc_std, pc_std, tscore_std, rank_std, pp_std, rscore_mania, acc_mania, pc_mania, tscore_mania, rank_mania, rscore_catch, acc_catch, pc_catch, tscore_catch, rank_catch, rscore_taiko, acc_taiko, pc_taiko, tscore_taiko, rank_taiko, pp_taiko, pp_catch, pp_mania, rscore_catch_rx, acc_catch_rx, pc_catch_rx, tscore_catch_rx, rank_catch_rx, rscore_taiko_rx, acc_taiko_rx, pc_taiko_rx, tscore_taiko_rx, rank_taiko_rx, rscore_std_ap, acc_std_ap, pc_std_ap, tscore_std_ap, rank_std_ap, rscore_std_rx, acc_std_rx, pc_std_rx, tscore_std_rx, rank_std_rx, pp_std_rx, pp_std_ap, pp_taiko_rx, pp_catch_rx) FROM stdin;
1	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0	0
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: tsunyoku
--

COPY public.users (id, name, email, pw, country, priv) FROM stdin;
1	Asahi		epic_bcrypt_goes_here	gb	1
\.


--
-- Name: channels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tsunyoku
--

SELECT pg_catalog.setval('public.channels_id_seq', 2, true);


--
-- Name: friends_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tsunyoku
--

SELECT pg_catalog.setval('public.friends_id_seq', 1, true);


--
-- Name: stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tsunyoku
--

SELECT pg_catalog.setval('public.stats_id_seq', 3, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tsunyoku
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (id);


--
-- Name: friends friends_pkey; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.friends
    ADD CONSTRAINT friends_pkey PRIMARY KEY (id);


--
-- Name: stats stats_pkey; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.stats
    ADD CONSTRAINT stats_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: tsunyoku
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

