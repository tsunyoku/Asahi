-- phpMyAdmin SQL Dump
-- version 4.6.6deb5ubuntu0.5
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Apr 20, 2021 at 08:10 PM
-- Server version: 5.7.33-0ubuntu0.18.04.1
-- PHP Version: 7.2.24-0ubuntu0.18.04.7

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
-- Table structure for table `friends`
--

CREATE TABLE `friends` (
  `id` int(11) NOT NULL,
  `user1` int(11) NOT NULL,
  `user2` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `name` varchar(16) NOT NULL,
  `email` varchar(254) NOT NULL DEFAULT '',
  `pw` text NOT NULL,
  `country` varchar(2) NOT NULL DEFAULT 'xx',
  `priv` int(11) NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `pw`, `country`, `priv`) VALUES
(1, 'Asahi', '', 'epic_bcrypt_goes_here', 'kp', 1);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `friends`
--
ALTER TABLE `friends`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `friends`
--
ALTER TABLE `friends`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1;
--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Table structure for table `stats`
--

CREATE TABLE `stats` (
  `id` int(11) NOT NULL,
  `rscore_std` int(255) NOT NULL DEFAULT '0',
  `acc_std` float(6,2) NOT NULL DEFAULT '0.00',
  `pc_std` int(255) NOT NULL DEFAULT '0',
  `tscore_std` int(255) NOT NULL DEFAULT '0',
  `rank_std` int(255) NOT NULL DEFAULT '0',
  `pp_std` int(255) NOT NULL DEFAULT '0',
  `rscore_mania` int(255) NOT NULL DEFAULT '0',
  `acc_mania` float(6,2) NOT NULL DEFAULT '0.00',
  `pc_mania` int(255) NOT NULL DEFAULT '0',
  `tscore_mania` int(255) NOT NULL DEFAULT '0',
  `rank_mania` int(255) NOT NULL DEFAULT '0',
  `rscore_catch` int(255) NOT NULL DEFAULT '0',
  `acc_catch` float(6,2) NOT NULL DEFAULT '0.00',
  `pc_catch` int(255) NOT NULL DEFAULT '0',
  `tscore_catch` int(255) NOT NULL DEFAULT '0',
  `rank_catch` int(255) NOT NULL DEFAULT '0',
  `rscore_taiko` int(255) NOT NULL DEFAULT '0',
  `acc_taiko` float(6,2) NOT NULL DEFAULT '0.00',
  `pc_taiko` int(255) NOT NULL DEFAULT '0',
  `tscore_taiko` int(255) NOT NULL DEFAULT '0',
  `rank_taiko` int(255) NOT NULL DEFAULT '0',
  `pp_taiko` int(255) NOT NULL DEFAULT '0',
  `pp_catch` int(255) NOT NULL DEFAULT '0',
  `pp_mania` int(255) NOT NULL DEFAULT '0',
  `rscore_catch_rx` int(255) NOT NULL DEFAULT '0',
  `acc_catch_rx` float(6,2) NOT NULL DEFAULT '0.00',
  `pc_catch_rx` int(255) NOT NULL DEFAULT '0',
  `tscore_catch_rx` int(255) NOT NULL DEFAULT '0',
  `rank_catch_rx` int(255) NOT NULL DEFAULT '0',
  `rscore_taiko_rx` int(255) NOT NULL DEFAULT '0',
  `acc_taiko_rx` float(6,2) NOT NULL DEFAULT '0.00',
  `pc_taiko_rx` int(255) NOT NULL DEFAULT '0',
  `tscore_taiko_rx` int(255) NOT NULL DEFAULT '0',
  `rank_taiko_rx` int(255) NOT NULL DEFAULT '0',
  `rscore_std_ap` int(255) NOT NULL DEFAULT '0',
  `acc_std_ap` float(6,2) NOT NULL DEFAULT '0.00',
  `pc_std_ap` int(255) NOT NULL DEFAULT '0',
  `tscore_std_ap` int(255) NOT NULL DEFAULT '0',
  `rank_std_ap` int(255) NOT NULL DEFAULT '0',
  `rscore_std_rx` int(255) NOT NULL DEFAULT '0',
  `acc_std_rx` float(6,2) NOT NULL DEFAULT '0.00',
  `pc_std_rx` int(255) NOT NULL DEFAULT '0',
  `tscore_std_rx` int(255) NOT NULL DEFAULT '0',
  `rank_std_rx` int(255) NOT NULL DEFAULT '0',
  `pp_std_rx` int(255) NOT NULL DEFAULT '0',
  `pp_std_ap` int(255) NOT NULL DEFAULT '0',
  `pp_taiko_rx` int(255) NOT NULL DEFAULT '0',
  `pp_catch_rx` int(255) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `stats`
--

INSERT INTO `stats` (`id`, `rscore_std`, `acc_std`, `pc_std`, `tscore_std`, `rank_std`, `pp_std`, `rscore_mania`, `acc_mania`, `pc_mania`, `tscore_mania`, `rank_mania`, `rscore_catch`, `acc_catch`, `pc_catch`, `tscore_catch`, `rank_catch`, `rscore_taiko`, `acc_taiko`, `pc_taiko`, `tscore_taiko`, `rank_taiko`, `pp_taiko`, `pp_catch`, `pp_mania`) VALUES
(1, 0, 0.00, 0, 0, 0, 0, 0, 0.00, 0, 0, 0, 0, 0.00, 0, 0, 0, 0, 0.00, 0, 0, 0, 0, 0, 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `stats`
--
ALTER TABLE `stats`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `stats`
--
ALTER TABLE `stats`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Table structure for table `channels`
--

CREATE TABLE `channels` (
  `id` int(11) NOT NULL,
  `name` text NOT NULL,
  `descr` text NOT NULL,
  `auto` int(1) NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `channels`
--

INSERT INTO `channels` (`id`, `name`, `descr`, `auto`) VALUES
(1, '#osu', 'So true!!!', 1),
(2, '#asahi', 'owo', 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `channels`
--
ALTER TABLE `channels`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `channels`
--
ALTER TABLE `channels`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

