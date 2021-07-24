-- phpMyAdmin SQL Dump
-- version 4.6.6deb5ubuntu0.5
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Jul 16, 2021 at 11:54 AM
-- Server version: 10.1.48-MariaDB-0ubuntu0.18.04.1
-- PHP Version: 7.2.24-0ubuntu0.18.04.8

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `asahi`
--

-- --------------------------------------------------------

--
-- Table structure for table `achievements`
--

CREATE TABLE `achievements` (
                                `id` int(11) NOT NULL,
                                `image` text NOT NULL,
                                `name` text NOT NULL,
                                `descr` text NOT NULL,
                                `cond` text NOT NULL,
                                `custom` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `achievements`
--

INSERT INTO `achievements` (`id`, `image`, `name`, `descr`, `cond`, `custom`) VALUES
(1, 'osu-skill-pass-1', 'Rising Star', 'Can\'t go forward without the first steps.', '(s.mods & 1 == 0) and 1 <= s.sr < 2 and s.mode.as_vn == 0', 0),
(2, 'osu-skill-pass-2', 'Constellation Prize', 'Definitely not a consolation prize. Now things start getting hard!', '(s.mods & 1 == 0) and 2 <= s.sr < 3 and s.mode.as_vn == 0', 0),
(3, 'osu-skill-pass-3', 'Building Confidence', 'Oh, you\'ve SO got this.', '(s.mods & 1 == 0) and 3 <= s.sr < 4 and s.mode.as_vn == 0', 0),
(4, 'osu-skill-pass-4', 'Insanity Approaches', 'You\'re not twitching, you\'re just ready.', '(s.mods & 1 == 0) and 4 <= s.sr < 5 and s.mode.as_vn == 0', 0),
(5, 'osu-skill-pass-5', 'These Clarion Skies', 'Everything seems so clear now.', '(s.mods & 1 == 0) and 5 <= s.sr < 6 and s.mode.as_vn == 0', 0),
(6, 'osu-skill-pass-6', 'Above and Beyond', 'A cut above the rest.', '(s.mods & 1 == 0) and 6 <= s.sr < 7 and s.mode.as_vn == 0', 0),
(7, 'osu-skill-pass-7', 'Supremacy', 'All marvel before your prowess.', '(s.mods & 1 == 0) and 7 <= s.sr < 8 and s.mode.as_vn == 0', 0),
(8, 'osu-skill-pass-8', 'Absolution', 'My god, you\'re full of stars!', '(s.mods & 1 == 0) and 8 <= s.sr < 9 and s.mode.as_vn == 0', 0),
(9, 'osu-skill-pass-9', 'Event Horizon', 'No force dares to pull you under.', '(s.mods & 1 == 0) and 9 <= s.sr < 10 and s.mode.as_vn == 0', 0),
(10, 'osu-skill-pass-10', 'Phantasm', 'Fevered is your passion, extraordinary is your skill.', '(s.mods & 1 == 0) and 10 <= s.sr < 11 and s.mode.as_vn == 0', 0),
(11, 'osu-skill-fc-1', 'Totality', 'All the notes. Every single one.', 's.fc and 1 <= s.sr < 2 and s.mode.as_vn == 0', 0),
(12, 'osu-skill-fc-2', 'Business As Usual', 'Two to go, please.', 's.fc and 2 <= s.sr < 3 and s.mode.as_vn == 0', 0),
(13, 'osu-skill-fc-3', 'Building Steam', 'Hey, this isn\'t so bad.', 's.fc and 3 <= s.sr < 4 and s.mode.as_vn == 0', 0),
(14, 'osu-skill-fc-4', 'Moving Forward', 'Bet you feel good about that.', 's.fc and 4 <= s.sr < 5 and s.mode.as_vn == 0', 0),
(15, 'osu-skill-fc-5', 'Paradigm Shift', 'Surprisingly difficult.', 's.fc and 5 <= s.sr < 6 and s.mode.as_vn == 0', 0),
(16, 'osu-skill-fc-6', 'Anguish Quelled', 'Don\'t choke.', 's.fc and 6 <= s.sr < 7 and s.mode.as_vn == 0', 0),
(17, 'osu-skill-fc-7', 'Never Give Up', 'Excellence is its own reward.', 's.fc and 7 <= s.sr < 8 and s.mode.as_vn == 0', 0),
(18, 'osu-skill-fc-8', 'Aberration', 'They said it couldn\'t be done. They were wrong.', 's.fc and 8 <= s.sr < 9 and s.mode.as_vn == 0', 0),
(19, 'osu-skill-fc-9', 'Chosen', 'Reign among the Prometheans, where you belong.', 's.fc and 9 <= s.sr < 10 and s.mode.as_vn == 0', 0),
(20, 'osu-skill-fc-10', 'Unfathomable', 'You have no equal.', 's.fc and 10 <= s.sr < 11 and s.mode.as_vn == 0', 0),
(21, 'osu-combo-500', '500 Combo', '500 big ones! You\'re moving up in the world!', '500 <= s.combo < 750 and s.mode.as_vn == 0', 0),
(22, 'osu-combo-750', '750 Combo', '750 notes back to back? Woah.', '750 <= s.combo < 1000 and s.mode.as_vn == 0', 0),
(23, 'osu-combo-1000', '1000 Combo', 'A thousand reasons why you rock at this game.', '1000 <= s.combo < 2000 and s.mode.as_vn == 0', 0),
(24, 'osu-combo-2000', '2000 Combo', 'Nothing can stop you now.', '2000 <= s.combo and s.mode.as_vn == 0', 0),
(25, 'taiko-skill-pass-1', 'My First Don', 'Marching to the beat of your own drum. Literally.', '(s.mods & 1 == 0) and 1 <= s.sr < 2 and s.mode.as_vn == 1', 0),
(26, 'taiko-skill-pass-2', 'Katsu Katsu Katsu', 'Hora! Izuko!', '(s.mods & 1 == 0) and 2 <= s.sr < 3 and s.mode.as_vn == 1', 0),
(27, 'taiko-skill-pass-3', 'Not Even Trying', 'Muzukashii? Not even.', '(s.mods & 1 == 0) and 3 <= s.sr < 4 and s.mode.as_vn == 1', 0),
(28, 'taiko-skill-pass-4', 'Face Your Demons', 'The first trials are now behind you, but are you a match for the Oni?', '(s.mods & 1 == 0) and 4 <= s.sr < 5 and s.mode.as_vn == 1', 0),
(29, 'taiko-skill-pass-5', 'The Demon Within', 'No rest for the wicked.', '(s.mods & 1 == 0) and 5 <= s.sr < 6 and s.mode.as_vn == 1', 0),
(30, 'taiko-skill-pass-6', 'Drumbreaker', 'Too strong.', '(s.mods & 1 == 0) and 6 <= s.sr < 7 and s.mode.as_vn == 1', 0),
(31, 'taiko-skill-pass-7', 'The Godfather', 'You are the Don of Dons.', '(s.mods & 1 == 0) and 7 <= s.sr < 8 and s.mode.as_vn == 1', 0),
(32, 'taiko-skill-pass-8', 'Rhythm Incarnate', 'Feel the beat. Become the beat.', '(s.mods & 1 == 0) and 8 <= s.sr < 9 and s.mode.as_vn == 1', 0),
(33, 'taiko-skill-fc-1', 'Keeping Time', 'Don, then katsu. Don, then katsu..', 's.fc and 1 <= s.sr < 2 and s.mode.as_vn == 1', 0),
(34, 'taiko-skill-fc-2', 'To Your Own Beat', 'Straight and steady.', 's.fc and 2 <= s.sr < 3 and s.mode.as_vn == 1', 0),
(35, 'taiko-skill-fc-3', 'Big Drums', 'Bigger scores to match.', 's.fc and 3 <= s.sr < 4 and s.mode.as_vn == 1', 0),
(36, 'taiko-skill-fc-4', 'Adversity Overcome', 'Difficult? Not for you.', 's.fc and 4 <= s.sr < 5 and s.mode.as_vn == 1', 0),
(37, 'taiko-skill-fc-5', 'Demonslayer', 'An Oni felled forevermore.', 's.fc and 5 <= s.sr < 6 and s.mode.as_vn == 1', 0),
(38, 'taiko-skill-fc-6', 'Rhythm\'s Call', 'Heralding true skill.', 's.fc and 6 <= s.sr < 7 and s.mode.as_vn == 1', 0),
(39, 'taiko-skill-fc-7', 'Time Everlasting', 'Not a single beat escapes you.', 's.fc and 7 <= s.sr < 8 and s.mode.as_vn == 1', 0),
(40, 'taiko-skill-fc-8', 'The Drummer\'s Throne', 'Percussive brilliance befitting royalty alone.', 's.fc and 8 <= s.sr < 9 and s.mode.as_vn == 1', 0),
(41, 'fruits-skill-pass-1', 'A Slice Of Life', 'Hey, this fruit catching business isn\'t bad.', '(s.mods & 1 == 0) and 1 <= s.sr < 2 and s.mode.as_vn == 2', 0),
(42, 'fruits-skill-pass-2', 'Dashing Ever Forward', 'Fast is how you do it.', '(s.mods & 1 == 0) and 2 <= s.sr < 3 and s.mode.as_vn == 2', 0),
(43, 'fruits-skill-pass-3', 'Zesty Disposition', 'No scurvy for you, not with that much fruit.', '(s.mods & 1 == 0) and 3 <= s.sr < 4 and s.mode.as_vn == 2', 0),
(44, 'fruits-skill-pass-4', 'Hyperdash ON!', 'Time and distance is no obstacle to you.', '(s.mods & 1 == 0) and 4 <= s.sr < 5 and s.mode.as_vn == 2', 0),
(45, 'fruits-skill-pass-5', 'It\'s Raining Fruit', 'And you can catch them all.', '(s.mods & 1 == 0) and 5 <= s.sr < 6 and s.mode.as_vn == 2', 0),
(46, 'fruits-skill-pass-6', 'Fruit Ninja', 'Legendary techniques.', '(s.mods & 1 == 0) and 6 <= s.sr < 7 and s.mode.as_vn == 2', 0),
(47, 'fruits-skill-pass-7', 'Dreamcatcher', 'No fruit, only dreams now.', '(s.mods & 1 == 0) and 7 <= s.sr < 8 and s.mode.as_vn == 2', 0),
(48, 'fruits-skill-pass-8', 'Lord of the Catch', 'Your kingdom kneels before you.', '(s.mods & 1 == 0) and 8 <= s.sr < 9 and s.mode.as_vn == 2', 0),
(49, 'fruits-skill-fc-1', 'Sweet And Sour', 'Apples and oranges, literally.', 's.fc and 1 <= s.sr < 2 and s.mode.as_vn == 2', 0),
(50, 'fruits-skill-fc-2', 'Reaching The Core', 'The seeds of future success.', 's.fc and 2 <= s.sr < 3 and s.mode.as_vn == 2', 0),
(51, 'fruits-skill-fc-3', 'Clean Platter', 'Clean only of failure. It is completely full, otherwise.', 's.fc and 3 <= s.sr < 4 and s.mode.as_vn == 2', 0),
(52, 'fruits-skill-fc-4', 'Between The Rain', 'No umbrella needed.', 's.fc and 4 <= s.sr < 5 and s.mode.as_vn == 2', 0),
(53, 'fruits-skill-fc-5', 'Addicted', 'That was an overdose?', 's.fc and 5 <= s.sr < 6 and s.mode.as_vn == 2', 0),
(54, 'fruits-skill-fc-6', 'Quickening', 'A dash above normal limits.', 's.fc and 6 <= s.sr < 7 and s.mode.as_vn == 2', 0),
(55, 'fruits-skill-fc-7', 'Supersonic', 'Faster than is reasonably necessary.', 's.fc and 7 <= s.sr < 8 and s.mode.as_vn == 2', 0),
(56, 'fruits-skill-fc-8', 'Dashing Scarlet', 'Speed beyond mortal reckoning.', 's.fc and 8 <= s.sr < 9 and s.mode.as_vn == 2', 0),
(57, 'mania-skill-pass-1', 'First Steps', 'It isn\'t 9-to-5, but 1-to-9. Keys, that is.', '(s.mods & 1 == 0) and 1 <= s.sr < 2 and s.mode.as_vn == 3', 0),
(58, 'mania-skill-pass-2', 'No Normal Player', 'Not anymore, at least.', '(s.mods & 1 == 0) and 2 <= s.sr < 3 and s.mode.as_vn == 3', 0),
(59, 'mania-skill-pass-3', 'Impulse Drive', 'Not quite hyperspeed, but getting close.', '(s.mods & 1 == 0) and 3 <= s.sr < 4 and s.mode.as_vn == 3', 0),
(60, 'mania-skill-pass-4', 'Hyperspeed', 'Woah.', '(s.mods & 1 == 0) and 4 <= s.sr < 5 and s.mode.as_vn == 3', 0),
(61, 'mania-skill-pass-5', 'Ever Onwards', 'Another challenge is just around the corner.', '(s.mods & 1 == 0) and 5 <= s.sr < 6 and s.mode.as_vn == 3', 0),
(62, 'mania-skill-pass-6', 'Another Surpassed', 'Is there no limit to your skills?', '(s.mods & 1 == 0) and 6 <= s.sr < 7 and s.mode.as_vn == 3', 0),
(63, 'mania-skill-pass-7', 'Extra Credit', 'See me after class.', '(s.mods & 1 == 0) and 7 <= s.sr < 8 and s.mode.as_vn == 3', 0),
(64, 'mania-skill-pass-8', 'Maniac', 'There\'s just no stopping you.', '(s.mods & 1 == 0) and 8 <= s.sr < 9 and s.mode.as_vn == 3', 0),
(65, 'mania-skill-fc-1', 'Keystruck', 'The beginning of a new story', 's.fc and 1 <= s.sr < 2 and s.mode.as_vn == 3', 0),
(66, 'mania-skill-fc-2', 'Keying In', 'Finding your groove.', 's.fc and 2 <= s.sr < 3 and s.mode.as_vn == 3', 0),
(67, 'mania-skill-fc-3', 'Hyperflow', 'You can *feel* the rhythm.', 's.fc and 3 <= s.sr < 4 and s.mode.as_vn == 3', 0),
(68, 'mania-skill-fc-4', 'Breakthrough', 'Many skills mastered, rolled into one.', 's.fc and 4 <= s.sr < 5 and s.mode.as_vn == 3', 0),
(69, 'mania-skill-fc-5', 'Everything Extra', 'Giving your all is giving everything you have.', 's.fc and 5 <= s.sr < 6 and s.mode.as_vn == 3', 0),
(70, 'mania-skill-fc-6', 'Level Breaker', 'Finesse beyond reason', 's.fc and 6 <= s.sr < 7 and s.mode.as_vn == 3', 0),
(71, 'mania-skill-fc-7', 'Step Up', 'A precipice rarely seen.', 's.fc and 7 <= s.sr < 8 and s.mode.as_vn == 3', 0),
(72, 'mania-skill-fc-8', 'Behind The Veil', 'Supernatural!', 's.fc and 8 <= s.sr < 9 and s.mode.as_vn == 3', 0);

-- --------------------------------------------------------

--
-- Table structure for table `channels`
--

CREATE TABLE `channels` (
  `id` int(11) NOT NULL,
  `name` text NOT NULL,
  `descr` text NOT NULL,
  `auto` int(11) NOT NULL DEFAULT '1',
  `perm` int(11) NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `channels`
--

INSERT INTO `channels` (`id`, `name`, `descr`, `auto`, `perm`) VALUES
(1, '#osu', 'So true!!!', 1, 1),
(2, '#asahi', 'owo', 0, 1);

-- --------------------------------------------------------

--
-- Table structure for table `clans`
--

CREATE TABLE `clans` (
  `id` int(11) NOT NULL,
  `name` varchar(16) NOT NULL,
  `tag` text NOT NULL,
  `owner` int(11) NOT NULL,
  `score` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `friends`
--

CREATE TABLE `friends` (
  `user1` int(11) NOT NULL,
  `user2` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `maps`
--

CREATE TABLE `maps` (
  `id` bigint(20) NOT NULL,
  `sid` bigint(20) NOT NULL,
  `md5` char(32) NOT NULL,
  `bpm` float NOT NULL,
  `cs` float NOT NULL,
  `ar` float NOT NULL,
  `od` float NOT NULL,
  `hp` float NOT NULL,
  `sr` float NOT NULL,
  `mode` int(11) NOT NULL,
  `artist` text NOT NULL,
  `title` text NOT NULL,
  `diff` text NOT NULL,
  `mapper` text NOT NULL,
  `status` int(11) NOT NULL,
  `frozen` int(11) NOT NULL,
  `update` bigint(20) NOT NULL,
  `nc` bigint(20) NOT NULL DEFAULT '0',
  `plays` int(11) NOT NULL DEFAULT '0',
  `passes` int(11) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `punishments`
--

CREATE TABLE `punishments` (
  `id` int(11) NOT NULL,
  `type` text NOT NULL,
  `reason` text NOT NULL,
  `target` int(11) NOT NULL,
  `from` int(11) NOT NULL,
  `time` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `requests`
--

CREATE TABLE `requests` (
  `id` int(11) NOT NULL,
  `requester` text NOT NULL,
  `map` bigint(20) NOT NULL,
  `status` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `scores`
--

CREATE TABLE `scores` (
  `id` int(11) NOT NULL,
  `md5` char(32) NOT NULL,
  `score` bigint(20) NOT NULL,
  `acc` float NOT NULL,
  `pp` float NOT NULL,
  `combo` int(11) NOT NULL,
  `mods` int(11) NOT NULL,
  `n300` int(11) NOT NULL,
  `geki` int(11) NOT NULL,
  `n100` int(11) NOT NULL,
  `katu` int(11) NOT NULL,
  `n50` int(11) NOT NULL,
  `miss` int(11) NOT NULL,
  `grade` char(3) NOT NULL DEFAULT 'F',
  `status` int(11) NOT NULL,
  `mode` int(11) NOT NULL,
  `time` int(11) NOT NULL,
  `uid` int(11) NOT NULL,
  `readable_mods` text NOT NULL,
  `fc` int(11) NOT NULL,
  `osuver` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `scores_ap`
--

CREATE TABLE `scores_ap` (
  `id` int(11) NOT NULL,
  `md5` char(32) NOT NULL,
  `score` bigint(20) NOT NULL,
  `acc` float NOT NULL,
  `pp` float NOT NULL,
  `combo` int(11) NOT NULL,
  `mods` int(11) NOT NULL,
  `n300` int(11) NOT NULL,
  `geki` int(11) NOT NULL,
  `n100` int(11) NOT NULL,
  `katu` int(11) NOT NULL,
  `n50` int(11) NOT NULL,
  `miss` int(11) NOT NULL,
  `grade` char(3) NOT NULL DEFAULT 'F',
  `status` int(11) NOT NULL,
  `mode` int(11) NOT NULL,
  `time` int(11) NOT NULL,
  `uid` int(11) NOT NULL,
  `readable_mods` text NOT NULL,
  `fc` int(11) NOT NULL,
  `osuver` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `scores_rx`
--

CREATE TABLE `scores_rx` (
  `id` int(11) NOT NULL,
  `md5` char(32) NOT NULL,
  `score` bigint(20) NOT NULL,
  `acc` float NOT NULL,
  `pp` float NOT NULL,
  `combo` int(11) NOT NULL,
  `mods` int(11) NOT NULL,
  `n300` int(11) NOT NULL,
  `geki` int(11) NOT NULL,
  `n100` int(11) NOT NULL,
  `katu` int(11) NOT NULL,
  `n50` int(11) NOT NULL,
  `miss` int(11) NOT NULL,
  `grade` char(3) NOT NULL DEFAULT 'F',
  `status` int(11) NOT NULL,
  `mode` int(11) NOT NULL,
  `time` int(11) NOT NULL,
  `uid` int(11) NOT NULL,
  `readable_mods` text NOT NULL,
  `fc` int(11) NOT NULL,
  `osuver` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `stats`
--

CREATE TABLE `stats` (
  `id` bigint(20) NOT NULL,
  `rscore_std` bigint(20) NOT NULL DEFAULT '0',
  `acc_std` double NOT NULL DEFAULT '0',
  `pc_std` bigint(20) NOT NULL DEFAULT '0',
  `tscore_std` bigint(20) NOT NULL DEFAULT '0',
  `pp_std` bigint(20) NOT NULL DEFAULT '0',
  `rscore_mania` bigint(20) NOT NULL DEFAULT '0',
  `acc_mania` double NOT NULL DEFAULT '0',
  `pc_mania` bigint(20) NOT NULL DEFAULT '0',
  `tscore_mania` bigint(20) NOT NULL DEFAULT '0',
  `rscore_catch` bigint(20) NOT NULL DEFAULT '0',
  `acc_catch` double NOT NULL DEFAULT '0',
  `pc_catch` bigint(20) NOT NULL DEFAULT '0',
  `tscore_catch` bigint(20) NOT NULL DEFAULT '0',
  `rscore_taiko` bigint(20) NOT NULL DEFAULT '0',
  `acc_taiko` double NOT NULL DEFAULT '0',
  `pc_taiko` bigint(20) NOT NULL DEFAULT '0',
  `tscore_taiko` bigint(20) NOT NULL DEFAULT '0',
  `pp_taiko` bigint(20) NOT NULL DEFAULT '0',
  `pp_catch` bigint(20) NOT NULL DEFAULT '0',
  `pp_mania` bigint(20) NOT NULL DEFAULT '0',
  `rscore_catch_rx` bigint(20) NOT NULL DEFAULT '0',
  `acc_catch_rx` double NOT NULL DEFAULT '0',
  `pc_catch_rx` bigint(20) NOT NULL DEFAULT '0',
  `tscore_catch_rx` bigint(20) NOT NULL DEFAULT '0',
  `rscore_taiko_rx` bigint(20) NOT NULL DEFAULT '0',
  `acc_taiko_rx` double NOT NULL DEFAULT '0',
  `pc_taiko_rx` bigint(20) NOT NULL DEFAULT '0',
  `tscore_taiko_rx` bigint(20) NOT NULL DEFAULT '0',
  `rscore_std_ap` bigint(20) NOT NULL DEFAULT '0',
  `acc_std_ap` double NOT NULL DEFAULT '0',
  `pc_std_ap` bigint(20) NOT NULL DEFAULT '0',
  `tscore_std_ap` bigint(20) NOT NULL DEFAULT '0',
  `rscore_std_rx` bigint(20) NOT NULL DEFAULT '0',
  `acc_std_rx` double NOT NULL DEFAULT '0',
  `pc_std_rx` bigint(20) NOT NULL DEFAULT '0',
  `tscore_std_rx` bigint(20) NOT NULL DEFAULT '0',
  `pp_std_rx` bigint(20) NOT NULL DEFAULT '0',
  `pp_std_ap` bigint(20) NOT NULL DEFAULT '0',
  `pp_taiko_rx` bigint(20) NOT NULL DEFAULT '0',
  `pp_catch_rx` bigint(20) NOT NULL DEFAULT '0',
  `mc_std` bigint(20) NOT NULL DEFAULT '0',
  `mc_std_rx` bigint(20) NOT NULL DEFAULT '0',
  `mc_std_ap` bigint(20) NOT NULL DEFAULT '0',
  `mc_taiko` bigint(20) NOT NULL DEFAULT '0',
  `mc_taiko_rx` bigint(20) NOT NULL DEFAULT '0',
  `mc_catch` bigint(20) NOT NULL DEFAULT '0',
  `mc_catch_rx` bigint(20) NOT NULL DEFAULT '0',
  `mc_mania` bigint(20) NOT NULL DEFAULT '0',
  `pt_std` bigint(20) NOT NULL DEFAULT '0',
  `pt_std_rx` bigint(20) NOT NULL DEFAULT '0',
  `pt_std_ap` bigint(20) NOT NULL DEFAULT '0',
  `pt_taiko` bigint(20) NOT NULL DEFAULT '0',
  `pt_taiko_rx` bigint(20) NOT NULL DEFAULT '0',
  `pt_catch` bigint(20) NOT NULL DEFAULT '0',
  `pt_catch_rx` bigint(20) NOT NULL DEFAULT '0',
  `pt_mania` bigint(20) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `stats` (`id`, `rscore_std`, `acc_std`, `pc_std`, `tscore_std`, `pp_std`, `rscore_mania`, `acc_mania`, `pc_mania`, `tscore_mania`, `rscore_catch`, `acc_catch`, `pc_catch`, `tscore_catch`, `rscore_taiko`, `acc_taiko`, `pc_taiko`, `tscore_taiko`, `pp_taiko`, `pp_catch`, `pp_mania`, `rscore_catch_rx`, `acc_catch_rx`, `pc_catch_rx`, `tscore_catch_rx`, `rscore_taiko_rx`, `acc_taiko_rx`, `pc_taiko_rx`, `tscore_taiko_rx`, `rscore_std_ap`, `acc_std_ap`, `pc_std_ap`, `tscore_std_ap`, `rscore_std_rx`, `acc_std_rx`, `pc_std_rx`, `tscore_std_rx`, `pp_std_rx`, `pp_std_ap`, `pp_taiko_rx`, `pp_catch_rx`, `mc_std`, `mc_std_rx`, `mc_std_ap`, `mc_taiko`, `mc_taiko_rx`, `mc_catch`, `mc_catch_rx`, `mc_mania`, `pt_std`, `pt_std_rx`, `pt_std_ap`, `pt_taiko`, `pt_taiko_rx`, `pt_catch`, `pt_catch_rx`, `pt_mania`) VALUES
(1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `name` varchar(16) NOT NULL,
  `email` varchar(32) NOT NULL,
  `pw` text NOT NULL,
  `country` char(2) NOT NULL DEFAULT 'xx',
  `priv` int(11) NOT NULL DEFAULT '1',
  `safe_name` varchar(16) NOT NULL,
  `clan` int(11) NOT NULL DEFAULT '0',
  `freeze_timer` bigint(20) NOT NULL DEFAULT '0',
  `registered_at` bigint(20) NOT NULL,
  `silence_end` bigint(20) NOT NULL DEFAULT '0',
  `donor_end` bigint(20) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `users` (`id`, `name`, `email`, `pw`, `country`, `priv`, `safe_name`, `clan`, `freeze_timer`, `registered_at`, `silence_end`, `donor_end`) VALUES
(1, 'Asahi', '', 'epic_bcrypt_goes_here', 'gb', 1, 'asahi', 0, 0, 0, 0, 0);

-- --------------------------------------------------------

--
-- Table structure for table `user_achievements`
--

CREATE TABLE `user_achievements` (
  `id` int(11) NOT NULL,
  `uid` int(11) NOT NULL,
  `ach` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `user_hashes`
--

CREATE TABLE `user_hashes` (
  `uid` int(11) NOT NULL,
  `mac_address` varchar(64) NOT NULL,
  `uninstall_id` varchar(64) NOT NULL,
  `disk_serial` varchar(64) NOT NULL,
  `ip` varchar(64) NOT NULL,
  `occurrences` bigint(20) NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Table structure for table `favourites`
--

CREATE TABLE `favourites` (
  `uid` int(11) NOT NULL,
  `sid` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Table structure for table `ratings`
--

CREATE TABLE `ratings` (
  `uid` int(11) NOT NULL,
  `md5` varchar(64) NOT NULL,
  `rating` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `achievements`
--
ALTER TABLE `achievements`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `channels`
--
ALTER TABLE `channels`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `clans`
--
ALTER TABLE `clans`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `friends`
--
ALTER TABLE `friends`
  ADD PRIMARY KEY (`user1`,`user2`);

--
-- Indexes for table `maps`
--
ALTER TABLE `maps`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `md5` (`md5`);

--
-- Indexes for table `punishments`
--
ALTER TABLE `punishments`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `requests`
--
ALTER TABLE `requests`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `scores`
--
ALTER TABLE `scores`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `scores_ap`
--
ALTER TABLE `scores_ap`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `scores_rx`
--
ALTER TABLE `scores_rx`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `stats`
--
ALTER TABLE `stats`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `user_achievements`
--
ALTER TABLE `user_achievements`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uid` (`uid`,`ach`);

--
-- Indexes for table `user_hashes`
--
ALTER TABLE `user_hashes`
  ADD UNIQUE KEY `uid` (`uid`,`mac_address`,`uninstall_id`,`disk_serial`,`ip`);

--
-- Indexes for table `favourites`
--
ALTER TABLE `favourites`
  ADD UNIQUE KEY `uid` (`uid`,`sid`);

--
-- Indexes for table `ratings`
--
ALTER TABLE `ratings`
  ADD UNIQUE KEY `uid` (`uid`,`md5`,`rating`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `achievements`
--
ALTER TABLE `achievements`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=73;
--
-- AUTO_INCREMENT for table `channels`
--
ALTER TABLE `channels`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
--
-- AUTO_INCREMENT for table `clans`
--
ALTER TABLE `clans`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;
--
-- AUTO_INCREMENT for table `punishments`
--
ALTER TABLE `punishments`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;
--
-- AUTO_INCREMENT for table `requests`
--
ALTER TABLE `requests`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `scores`
--
ALTER TABLE `scores`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;
--
-- AUTO_INCREMENT for table `scores_ap`
--
ALTER TABLE `scores_ap`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;
--
-- AUTO_INCREMENT for table `scores_rx`
--
ALTER TABLE `scores_rx`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;
--
-- AUTO_INCREMENT for table `stats`
--
ALTER TABLE `stats`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
--
-- AUTO_INCREMENT for table `user_achievements`
--
ALTER TABLE `user_achievements`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
